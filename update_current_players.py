#!/usr/bin/env python3
"""Refresh the save files from the VM and rebuild current_players_simple.csv."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from extract_main_dat import (
    extract_current_players,
    write_csv,
)
from qcow2_ntfs_extract import extract_ntfs_folder_from_qcow2


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_VM_IMAGE = Path(
    "/Users/alberto/Library/Containers/com.utmapp.UTM/Data/Documents/"
    "WindowsXP.utm/Data/FF76F6F6-F896-4190-BBDC-8D7D26E6BFE5.qcow2"
)
DEFAULT_VM_SAVE_DIR = "CALCIO7/SAVE/PROMANAG/036-0"
DEFAULT_LOCAL_SAVE_DIR = REPO_ROOT / "SAVE/PROMANAG/036-0"
DEFAULT_STATIC_DB = REPO_ROOT / "DBDAT/jug99036.fdi"
DEFAULT_TEAM_DB = REPO_ROOT / "DBDAT/eq99036.fdi"
DEFAULT_OUTPUT = REPO_ROOT / "editor/main_dat_extract/current_players_simple.csv"

SAVE_FILES = ("main.dat", "estoff.dat", "estpart.dat", "esttemp.dat")
GENERATED_OUTPUTS = (
    "ascii_runs.csv",
    "candidate_player_records.csv",
    "candidate_player_records.json",
    "current_players_simple.csv",
    "current_players_stats.csv",
    "relaxed_stat_rows.csv",
    "relaxed_stat_rows.json",
    "summary.json",
    "u16_pair_runs.csv",
    "u16_pair_runs.json",
)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def find_seven_zip() -> str:
    for candidate in ("/opt/homebrew/bin/7z", "/usr/local/bin/7z", "7z"):
        found = shutil.which(candidate) if candidate == "7z" else candidate
        if found and Path(found).exists():
            return found
    raise FileNotFoundError("Could not find 7z. Install p7zip or set PATH so 7z is available.")


def image_open_hint(vm_image: Path) -> str:
    try:
        result = subprocess.run(
            ["lsof", str(vm_image)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""

    lines = [line for line in result.stdout.splitlines()[1:] if line.strip()]
    if not lines:
        return ""
    processes = ", ".join(sorted({line.split()[0] for line in lines if line.split()}))
    return f"\nThe VM disk image appears to be open by: {processes}. Shut down or suspend the VM and retry."


def concise_failure(output: str) -> str:
    interesting = []
    for line in output.splitlines():
        if "ERROR:" in line or "Open ERROR" in line or "WARNINGS:" in line:
            interesting.append(line)
    return "\n".join(interesting)


def extract_save_folder(vm_image: Path, vm_save_dir: str, destination: Path) -> Path:
    save_dir = vm_save_dir.strip("/").replace("\\", "/")
    archive_pattern = f"{save_dir}/*"

    try:
        seven_zip = find_seven_zip()
    except FileNotFoundError:
        open_hint = image_open_hint(vm_image)
        if open_hint:
            raise RuntimeError(f"The VM disk image is open.{open_hint}")
        return extract_ntfs_folder_from_qcow2(vm_image, save_dir, destination, SAVE_FILES)

    result = subprocess.run(
        [seven_zip, "x", "-y", f"-o{destination}", str(vm_image), archive_pattern],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = concise_failure(f"{result.stdout}\n{result.stderr}")
        open_hint = image_open_hint(vm_image)
        if not open_hint:
            try:
                return extract_ntfs_folder_from_qcow2(vm_image, save_dir, destination, SAVE_FILES)
            except Exception as fallback_error:
                raise RuntimeError(
                    "7z could not extract the save folder from the VM image, and the "
                    "direct qcow2/NTFS fallback also failed.\n"
                    f"{details}\n"
                    f"Fallback error: {fallback_error}"
                ) from fallback_error

        raise RuntimeError(
            "7z could not extract the save folder from the VM image.\n"
            f"{open_hint}\n"
            f"{details}"
        )

    extracted_save_dir = destination / save_dir
    if not (extracted_save_dir / "main.dat").exists():
        raise FileNotFoundError(f"main.dat was not found in {vm_image}:{save_dir}")
    return extracted_save_dir


def copy_save_files(extracted_save_dir: Path, local_save_dir: Path) -> list[str]:
    local_save_dir.mkdir(parents=True, exist_ok=True)

    for filename in SAVE_FILES:
        stale_file = local_save_dir / filename
        if stale_file.exists():
            stale_file.unlink()

    copied: list[str] = []
    for filename in SAVE_FILES:
        source = extracted_save_dir / filename
        if source.exists():
            shutil.copy2(source, local_save_dir / filename)
            copied.append(filename)

    if "main.dat" not in copied:
        raise FileNotFoundError("main.dat was not copied from the VM save folder.")
    return copied


def clean_generated_outputs(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for filename in GENERATED_OUTPUTS:
        generated_file = output_path.parent / filename
        if generated_file.exists():
            generated_file.unlink()


def refresh_current_players(
    vm_image: Path,
    vm_save_dir: str,
    local_save_dir: Path,
    static_db: Path,
    team_db: Path,
    output: Path,
    season_year: int | None,
) -> tuple[list[str], int]:
    with tempfile.TemporaryDirectory(prefix="calcio7-save-") as temporary_dir:
        extracted_save_dir = extract_save_folder(vm_image, vm_save_dir, Path(temporary_dir))
        copied = copy_save_files(extracted_save_dir, local_save_dir)

    rows = extract_current_players(local_save_dir / "main.dat", static_db, team_db, season_year)
    clean_generated_outputs(output)
    write_csv(output, rows)
    return copied, len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vm-image", type=Path, default=DEFAULT_VM_IMAGE)
    parser.add_argument("--vm-save-dir", default=DEFAULT_VM_SAVE_DIR)
    parser.add_argument("--local-save-dir", type=Path, default=DEFAULT_LOCAL_SAVE_DIR)
    parser.add_argument("--static-db", type=Path, default=DEFAULT_STATIC_DB)
    parser.add_argument("--team-db", type=Path, default=DEFAULT_TEAM_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--season-year", type=int, default=None)
    args = parser.parse_args()

    try:
        copied, player_count = refresh_current_players(
            vm_image=resolve_path(args.vm_image),
            vm_save_dir=args.vm_save_dir,
            local_save_dir=resolve_path(args.local_save_dir),
            static_db=resolve_path(args.static_db),
            team_db=resolve_path(args.team_db),
            output=resolve_path(args.output),
            season_year=args.season_year,
        )
    except Exception as error:
        raise SystemExit(str(error)) from error

    print(f"Copied save files: {', '.join(copied)}")
    print(f"Wrote {player_count} players to {resolve_path(args.output)}")


if __name__ == "__main__":
    main()
