#!/usr/bin/env python3

import argparse
from pathlib import Path


PATCH_OFFSET = 0xBB6BD
PATCH = bytes.fromhex(
    "33 ff a0 30 d8 89 00 84 c0 74 0c"
    " 8b ce e8 31 d2 ff ff 84 c0 75 01 47"
    " 8b ce e8 05 0c 00 00 85 c0 74 1a"
    " ff 70 34 8b 48 38 e8 26 7e 03 00"
    " 4f 75 0c 68 ff ff 00 00 8b ce e8 87 d0 ff ff"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="original MANAGCAL.EXE")
    parser.add_argument("output", type=Path, help="new executable to create")
    args = parser.parse_args()

    try:
        executable = bytearray(args.source.read_bytes())
        executable[PATCH_OFFSET : PATCH_OFFSET + len(PATCH)] = PATCH
        with args.output.open("xb") as output:
            output.write(executable)
    except OSError as error:
        parser.error(str(error))

    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
