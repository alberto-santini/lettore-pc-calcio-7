#!/usr/bin/env python3

import argparse
from pathlib import Path
from struct import pack


ROLLOVER_OFFSET = 0xBB6BD
ROLLOVER_PATCH = bytes.fromhex(
    "33 ff a0 30 d8 89 00 84 c0 74 0c"
    " 8b ce e8 31 d2 ff ff 84 c0 75 01 47"
    " 8b ce e8 05 0c 00 00 85 c0 74 1a"
    " ff 70 34 8b 48 38 e8 26 7e 03 00"
    " 4f 75 0c 68 ff ff 00 00 8b ce e8 87 d0 ff ff"
)

INFO_RESULT_CALL_OFFSET = 0x6496D
INFO_RESULT_CALL_PATCH = bytes.fromhex("e8 a1 f7 ff ff")

INFO_RESULT_HELPER_OFFSET = 0x64113
INFO_RESULT_HELPER = bytes.fromhex(
    "85 c0 75 03"
    " c2 1c 00"
    " e9 c1 54 32 00"
)

PALETTE_REFRESH_CALL_OFFSET = 0xE204
PALETTE_REFRESH_CALL_PATCH = bytes.fromhex("e8 9c ff ff ff")
PALETTE_REFRESH_HELPER_OFFSET = 0xE1A5
PALETTE_REFRESH_HELPER = bytes.fromhex(
    "e8 46 e6 37 00"
    " e9 a1 ed 36 00"
)

SEMIFINAL_DRAW_CALL_OFFSET = 0x1BA4AA
SEMIFINAL_DRAW_CALL_PATCH = bytes.fromhex("e8 81 60 25 00 90")

TEXT_SECTION_OFFSET = 0x1000
TEXT_VIRTUAL_SIZE_OFFSET = 0x208
SEMIFINAL_DRAW_HELPER_OFFSET = 0x410530
SEMIFINAL_DRAW_HELPER = bytes.fromhex(
    "8b 86 a0 0c 00 00 83 f8 04 0f 85 b0 00 00 00"
    " 39 86 60 0c 00 00 0f 85 a4 00 00 00"
    " 83 be 98 0c 00 00 08 0f 85 97 00 00 00"
    " 8b 96 5c 0c 00 00 85 d2 0f 84 89 00 00 00 53 57 89 d3 31 ff"
    " 47 83 ff 04 74 75 66 8b 04 7b 66 85 c0 74 f1"
    " 31 c9 66 3b 04 4b 74 07 41 39 f9 72 f5 eb e2"
    " 8b 96 94 0c 00 00 85 d2 74 53 69 cf b8 00 00 00"
    " 8d 94 0a e0 02 00 00 50 52 89 d1 e8 b6 78 d9 ff 5a 89 c1 58"
    " 83 f9 01 74 11 83 f9 02 75 b4 66 3b 42 38 75 ae 66 8b 42 36 eb 0a"
    " 66 3b 42 36 75 a2 66 8b 42 38"
    " 66 85 c0 74 99 31 c9 66 3b 04 4b 74 91 41 83 f9 04 72 f4"
    " 66 89 04 7b eb 85"
    " 5f 5b 8b 86 a0 0c 00 00 c3"
)

QUALIFIER_CALL_OFFSET = 0x157EF8
QUALIFIER_CALL_PATCH = bytes.fromhex("e8 03 87 2b 00 90 90")
QUALIFIER_HELPER_OFFSET = 0x410600
QUALIFIER_HELPER = bytes.fromhex(
    "66 89 86 0a 0c 00 00 66 85 c0 74 3a 66 3b 86 18 0c 00 00 75 31"
    " 8b 96 40 0c 00 00 85 d2 74 27"
    " 66 3b 42 36 75 06 66 8b 4a 38 eb 0a 66 3b 42 38 75 15 66 8b 4a 36"
    " 66 85 c9 74 0c 66 39 c1 74 07 66 89 8e 18 0c 00 00 c3"
)

UEFA_REGISTRATION_CALL_OFFSETS = (
    0x15AD9C, 0x15ADAA, 0x15ADE4, 0x15AE11, 0x15AE32, 0x15AE43, 0x15AE86,
    0x15AEBB, 0x15AEC9, 0x15AF0C, 0x15AF41, 0x15AF4C, 0x15AF96, 0x15AFD2,
)
UEFA_RANKED_CANDIDATE_OFFSET = 0x410650
UEFA_RANKED_CANDIDATE = bytes.fromhex(
    "8b 44 24 04 83 f0 03 66 8b 84 41 1c 0c 00 00 c2 04 00"
)
UEFA_PREVIEW_CALL_OFFSETS = (0x15C6BA, 0x15C6DF)
UEFA_PREVIEW_OFFSET = 0x410670
UEFA_PREVIEW = bytes.fromhex(
    "83 7c 24 04 02 0f 87 75 dd dc ff 56 53 57 83 ec"
    " 04 89 ce 80 be 38 0c 00 00 01 0f 85 ec 00 00 00"
    " 83 be 3c 0c 00 00 00 0f 85 df 00 00 00 b9 03 00 00 00"
    " 66 8b 84 4e 1c 0c 00 00 66 85 c0 0f 84 c9 00 00"
    " 00 89 ca 4a 78 0f 66 3b 84 56 1c 0c 00 00 75 f3"
    " e9 b5 00 00 00 49 79 d8"
    " c7 04 24 bb 0b 00 00 89 e0 50 b9 08 54 8a 00 e8"
    " b2 b7 d8 ff 85 c0 0f 84 96 00 00 00 83 b8 c4 0b"
    " 00 00 06 0f 85 89 00 00 00 0f b7 98 74 14 00 00 85 db 74 7e"
    " c7 04 24 8a 13 00 00 89 e0 50 b9 08 54 8a 00 e8"
    " 7e b7 d8 ff 85 c0 74 66 83 b8 2c 0c 00 00 08 75"
    " 5d 89 c1 8b 10 ff 92 bc 00 00 00 0f b7 f8 85 ff 74 4c"
    " 0f b7 86 22 0c 00 00 0f b7 96 20 0c 00 00 39 f8"
    " 75 04 89 d0 eb 04 39 fa 75 07 0f b7 96 1e 0c 00"
    " 00 39 c3 74 04 39 d3 75 07 0f b7 9e 1c 0c 00 00"
    " 8b 4c 24 14 85 c9 74 09 89 d0 83 f9 01 74 02 89"
    " d8 89 f1 83 c4 04 5f 5b 5e c2 04 00 89 f1 83 c4"
    " 04 5f 5b 5e e9 67 dc dc ff"
)

PATCHES = (
    (ROLLOVER_OFFSET, ROLLOVER_PATCH),
    (INFO_RESULT_CALL_OFFSET, INFO_RESULT_CALL_PATCH),
    (INFO_RESULT_HELPER_OFFSET, INFO_RESULT_HELPER),
    (PALETTE_REFRESH_CALL_OFFSET, PALETTE_REFRESH_CALL_PATCH),
    (PALETTE_REFRESH_HELPER_OFFSET, PALETTE_REFRESH_HELPER),
    (SEMIFINAL_DRAW_CALL_OFFSET, SEMIFINAL_DRAW_CALL_PATCH),
    (SEMIFINAL_DRAW_HELPER_OFFSET, SEMIFINAL_DRAW_HELPER),
    (QUALIFIER_CALL_OFFSET, QUALIFIER_CALL_PATCH),
    (QUALIFIER_HELPER_OFFSET, QUALIFIER_HELPER),
    (UEFA_RANKED_CANDIDATE_OFFSET, UEFA_RANKED_CANDIDATE),
    (UEFA_PREVIEW_OFFSET, UEFA_PREVIEW),
    (
        TEXT_VIRTUAL_SIZE_OFFSET,
        pack("<I", UEFA_PREVIEW_OFFSET + len(UEFA_PREVIEW) - TEXT_SECTION_OFFSET),
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="original MANAGCAL.EXE")
    parser.add_argument("output", type=Path, help="new executable to create")
    args = parser.parse_args()

    try:
        executable = bytearray(args.source.read_bytes())

        for offset, patch in PATCHES:
            executable[offset : offset + len(patch)] = patch

        for call_offsets, helper_offset in (
            (UEFA_REGISTRATION_CALL_OFFSETS, UEFA_RANKED_CANDIDATE_OFFSET),
            (UEFA_PREVIEW_CALL_OFFSETS, UEFA_PREVIEW_OFFSET),
        ):
            for offset in call_offsets:
                executable[offset : offset + 5] = b"\xe8" + pack("<i", helper_offset - offset - 5)

        with args.output.open("xb") as output:
            output.write(executable)
    except OSError as error:
        parser.error(str(error))

    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
