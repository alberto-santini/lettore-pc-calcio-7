#!/usr/bin/env python3

import argparse
from pathlib import Path


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

PATCHES = (
    (ROLLOVER_OFFSET, ROLLOVER_PATCH),
    (INFO_RESULT_CALL_OFFSET, INFO_RESULT_CALL_PATCH),
    (INFO_RESULT_HELPER_OFFSET, INFO_RESULT_HELPER),
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
        
        with args.output.open("xb") as output:
            output.write(executable)
    except OSError as error:
        parser.error(str(error))

    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
