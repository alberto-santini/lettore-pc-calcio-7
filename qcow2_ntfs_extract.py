"""Minimal qcow2/NTFS reader used to copy save files without mounting."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


def be_u32(data: bytes) -> int:
    return int.from_bytes(data, "big")


def be_u64(data: bytes) -> int:
    return int.from_bytes(data, "big")


def le_u16(data: bytes) -> int:
    return int.from_bytes(data, "little")


def le_u32(data: bytes) -> int:
    return int.from_bytes(data, "little")


def le_u64(data: bytes) -> int:
    return int.from_bytes(data, "little")


def le_i(data: bytes) -> int:
    return int.from_bytes(data, "little", signed=True)


@dataclass(frozen=True)
class NtfsFile:
    record_id: int
    name: str
    size: int
    non_resident: bool
    value: bytes | list[tuple[int, int | None, int]]


class Qcow2Reader:
    def __init__(self, path: Path):
        self.path = path
        self.handle = path.open("rb")
        header = self.handle.read(104)
        if len(header) < 104 or header[:4] != b"QFI\xfb":
            raise ValueError(f"{path} is not a qcow2 image")

        version = be_u32(header[4:8])
        if version not in (2, 3):
            raise ValueError(f"Unsupported qcow2 version {version}")
        if be_u32(header[32:36]) != 0:
            raise ValueError("Encrypted qcow2 images are not supported")

        self.cluster_bits = be_u32(header[20:24])
        self.cluster_size = 1 << self.cluster_bits
        self.l1_size = be_u32(header[36:40])
        self.l1_offset = be_u64(header[40:48])
        self.offset_mask = ((1 << 56) - 1) & ~(self.cluster_size - 1)
        self.l2_bits = self.cluster_bits - 3
        self.l2_mask = (1 << self.l2_bits) - 1
        self.l2_cache: dict[int, list[int]] = {}

        self.handle.seek(self.l1_offset)
        self.l1_table = [be_u64(self.handle.read(8)) for _ in range(self.l1_size)]

    def close(self) -> None:
        self.handle.close()

    def read_physical(self, offset: int, size: int) -> bytes:
        self.handle.seek(offset)
        return self.handle.read(size)

    def read(self, offset: int, size: int) -> bytes:
        output = bytearray()
        while size:
            virtual_cluster = offset // self.cluster_size
            within_cluster = offset % self.cluster_size
            chunk_size = min(size, self.cluster_size - within_cluster)

            entry = self.l2_entry(virtual_cluster)
            if entry == 0 or entry & 1:
                output.extend(b"\0" * chunk_size)
            elif entry & (1 << 62):
                raise ValueError("Compressed qcow2 clusters are not supported")
            else:
                physical_offset = (entry & self.offset_mask) + within_cluster
                output.extend(self.read_physical(physical_offset, chunk_size))

            offset += chunk_size
            size -= chunk_size
        return bytes(output)

    def l2_entry(self, virtual_cluster: int) -> int:
        l1_index = virtual_cluster >> self.l2_bits
        if l1_index >= len(self.l1_table):
            return 0

        l1_entry = self.l1_table[l1_index]
        if l1_entry == 0:
            return 0

        l2_offset = l1_entry & self.offset_mask
        if l2_offset not in self.l2_cache:
            raw = self.read_physical(l2_offset, self.cluster_size)
            self.l2_cache[l2_offset] = [
                be_u64(raw[offset : offset + 8])
                for offset in range(0, len(raw), 8)
            ]
        return self.l2_cache[l2_offset][virtual_cluster & self.l2_mask]


class NtfsReader:
    ROOT_RECORD = 5

    def __init__(self, disk: Qcow2Reader):
        self.disk = disk
        mbr = disk.read(0, 512)
        partition_offset = self.find_ntfs_partition_offset(mbr)
        boot = disk.read(partition_offset, 512)
        if boot[3:11] != b"NTFS    ":
            raise ValueError("The first NTFS partition does not contain an NTFS boot sector")

        self.partition_offset = partition_offset
        self.bytes_per_sector = le_u16(boot[0x0B:0x0D])
        self.cluster_size = self.bytes_per_sector * boot[0x0D]
        mft_lcn = le_u64(boot[0x30:0x38])
        record_size_code = struct.unpack("b", boot[0x40:0x41])[0]
        if record_size_code > 0:
            self.record_size = record_size_code * self.cluster_size
        else:
            self.record_size = 1 << abs(record_size_code)

        self.mft_offset = self.partition_offset + mft_lcn * self.cluster_size
        self.mft_runs: list[tuple[int, int | None, int]] = []
        self.mft_size = 0
        self.records: dict[int, dict[str, object]] = {}
        self.children: dict[tuple[int, str], int] = {}
        self.load_mft()

    @staticmethod
    def find_ntfs_partition_offset(mbr: bytes) -> int:
        for index in range(4):
            entry = mbr[0x1BE + index * 16 : 0x1BE + (index + 1) * 16]
            if len(entry) == 16 and entry[4] == 0x07:
                return le_u32(entry[8:12]) * 512
        raise ValueError("Could not find an NTFS partition in the qcow2 image")

    def read_volume(self, offset: int, size: int) -> bytes:
        return self.disk.read(self.partition_offset + offset, size)

    def load_mft(self) -> None:
        record = self.parse_record(self.disk.read(self.mft_offset, self.record_size))
        if record is None:
            raise ValueError("Could not read the NTFS MFT record")

        for data_attr in record["data_attrs"]:
            if data_attr.name == "":
                if not data_attr.non_resident:
                    raise ValueError("Unexpected resident $MFT data attribute")
                self.mft_size = data_attr.size
                self.mft_runs = data_attr.value  # type: ignore[assignment]
                break
        if not self.mft_runs:
            raise ValueError("Could not find the NTFS MFT data runs")

        for record_id in range(self.mft_size // self.record_size):
            parsed = self.parse_record(self.read_mft_record(record_id))
            if parsed is None or not (parsed["flags"] & 1):
                continue
            self.records[record_id] = parsed

            for name, parent_id in parsed["names"]:
                self.children[(parent_id, name.upper())] = record_id

    def read_mft_record(self, record_id: int) -> bytes:
        offset = record_id * self.record_size
        return self.read_from_runs(self.mft_runs, offset, self.record_size)

    def read_from_runs(
        self,
        runs: list[tuple[int, int | None, int]],
        offset: int,
        size: int,
    ) -> bytes:
        output = bytearray()
        while size:
            for vcn, lcn, cluster_count in runs:
                run_start = vcn * self.cluster_size
                run_end = run_start + cluster_count * self.cluster_size
                if run_start <= offset < run_end:
                    chunk_size = min(size, run_end - offset)
                    if lcn is None:
                        output.extend(b"\0" * chunk_size)
                    else:
                        run_offset = lcn * self.cluster_size + (offset - run_start)
                        output.extend(self.read_volume(run_offset, chunk_size))
                    offset += chunk_size
                    size -= chunk_size
                    break
            else:
                raise ValueError("Requested NTFS data is outside the available data runs")
        return bytes(output)

    def apply_fixup(self, raw: bytes) -> bytes:
        record = bytearray(raw)
        if record[:4] != b"FILE":
            return bytes(record)

        usa_offset = le_u16(record[4:6])
        usa_count = le_u16(record[6:8])
        usa = record[usa_offset : usa_offset + usa_count * 2]
        if len(usa) != usa_count * 2:
            return bytes(record)

        for index in range(1, usa_count):
            sector_end = index * self.bytes_per_sector - 2
            if sector_end + 2 <= len(record):
                record[sector_end : sector_end + 2] = usa[index * 2 : index * 2 + 2]
        return bytes(record)

    def parse_record(self, raw: bytes) -> dict[str, object] | None:
        record = self.apply_fixup(raw)
        if record[:4] != b"FILE":
            return None

        names: list[tuple[str, int]] = []
        data_attrs: list[NtfsFile] = []
        attr_offset = le_u16(record[0x14:0x16])
        flags = le_u16(record[0x16:0x18])

        while attr_offset + 8 <= len(record):
            attr_type = le_u32(record[attr_offset : attr_offset + 4])
            if attr_type == 0xFFFFFFFF:
                break

            attr_length = le_u32(record[attr_offset + 4 : attr_offset + 8])
            if attr_length < 16 or attr_offset + attr_length > len(record):
                break

            non_resident = record[attr_offset + 8] != 0
            attr_name_length = record[attr_offset + 9]
            attr_name_offset = le_u16(record[attr_offset + 10 : attr_offset + 12])
            attr_name = ""
            if attr_name_length:
                start = attr_offset + attr_name_offset
                end = start + attr_name_length * 2
                attr_name = record[start:end].decode("utf-16le", errors="replace")

            if non_resident:
                data_run_offset = le_u16(record[attr_offset + 0x20 : attr_offset + 0x22])
                real_size = le_u64(record[attr_offset + 0x30 : attr_offset + 0x38])
                value: bytes | list[tuple[int, int | None, int]] = self.parse_data_runs(
                    record[attr_offset + data_run_offset : attr_offset + attr_length]
                )
                value_size = real_size
            else:
                value_size = le_u32(record[attr_offset + 0x10 : attr_offset + 0x14])
                value_offset = le_u16(record[attr_offset + 0x14 : attr_offset + 0x16])
                value = record[attr_offset + value_offset : attr_offset + value_offset + value_size]

            if attr_type == 0x30 and isinstance(value, bytes) and len(value) >= 66:
                parent_id = le_u64(value[:8]) & ((1 << 48) - 1)
                name_length = value[64]
                name_start = 66
                name_end = name_start + name_length * 2
                name = value[name_start:name_end].decode("utf-16le", errors="replace")
                names.append((name, parent_id))
            elif attr_type == 0x80:
                data_attrs.append(
                    NtfsFile(
                        record_id=-1,
                        name=attr_name,
                        size=value_size,
                        non_resident=non_resident,
                        value=value,
                    )
                )

            attr_offset += attr_length

        return {"flags": flags, "names": names, "data_attrs": data_attrs}

    @staticmethod
    def parse_data_runs(data: bytes) -> list[tuple[int, int | None, int]]:
        runs: list[tuple[int, int | None, int]] = []
        offset = 0
        lcn = 0
        vcn = 0

        while offset < len(data) and data[offset] != 0:
            header = data[offset]
            offset += 1
            length_size = header & 0x0F
            lcn_delta_size = header >> 4

            cluster_count = le_u64(data[offset : offset + length_size] + b"\0" * (8 - length_size))
            offset += length_size

            if lcn_delta_size:
                lcn_delta = le_i(data[offset : offset + lcn_delta_size])
                offset += lcn_delta_size
                lcn += lcn_delta
                run_lcn: int | None = lcn
            else:
                run_lcn = None

            runs.append((vcn, run_lcn, cluster_count))
            vcn += cluster_count
        return runs

    def find_path(self, folder_path: str) -> int:
        record_id = self.ROOT_RECORD
        for component in folder_path.strip("/").replace("\\", "/").split("/"):
            if not component:
                continue
            key = (record_id, component.upper())
            if key not in self.children:
                raise FileNotFoundError(f"Could not find {folder_path!r} in the NTFS image")
            record_id = self.children[key]
        return record_id

    def child_file(self, parent_id: int, filename: str) -> NtfsFile | None:
        record_id = self.children.get((parent_id, filename.upper()))
        if record_id is None:
            return None

        record = self.records.get(record_id)
        if record is None:
            return None

        for data_attr in record["data_attrs"]:
            if data_attr.name == "":
                return NtfsFile(
                    record_id=record_id,
                    name=filename,
                    size=data_attr.size,
                    non_resident=data_attr.non_resident,
                    value=data_attr.value,
                )
        return None

    def read_file(self, ntfs_file: NtfsFile) -> bytes:
        if ntfs_file.non_resident:
            return self.read_from_runs(ntfs_file.value, 0, ntfs_file.size)  # type: ignore[arg-type]
        return ntfs_file.value[: ntfs_file.size]  # type: ignore[index]


def extract_ntfs_folder_from_qcow2(
    image_path: Path,
    folder_path: str,
    destination: Path,
    filenames: tuple[str, ...],
) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    disk = Qcow2Reader(image_path)
    try:
        ntfs = NtfsReader(disk)
        source_folder_id = ntfs.find_path(folder_path)
        target_folder = destination / folder_path.strip("/").replace("\\", "/")
        target_folder.mkdir(parents=True, exist_ok=True)

        copied = 0
        for filename in filenames:
            source_file = ntfs.child_file(source_folder_id, filename)
            if source_file is None:
                continue
            (target_folder / filename).write_bytes(ntfs.read_file(source_file))
            copied += 1

        if copied == 0:
            raise FileNotFoundError(f"No requested files were found in {folder_path!r}")
        return target_folder
    finally:
        disk.close()
