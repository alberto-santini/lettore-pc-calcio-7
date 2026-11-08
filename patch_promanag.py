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

PALETTE_REFRESH_CALL_OFFSET = 0xE204
PALETTE_REFRESH_CALL_PATCH = bytes.fromhex("e8 9c ff ff ff")
PALETTE_REFRESH_HELPER_OFFSET = 0xE1A5
PALETTE_REFRESH_HELPER = bytes.fromhex(
    "e8 46 e6 37 00"
    " e9 a1 ed 36 00"
)

QUALIFIER_CALL_OFFSET = 0x157EF8
QUALIFIER_CALL_PATCH = bytes.fromhex("e8 03 87 2b 00 90 90")  # call 0x810600; nop; nop
QUALIFIER_HELPER_OFFSET = 0x410600
QUALIFIER_HELPER = bytes.fromhex(
    # Store the confirmed runner-up in [esi+0xc0a] as before. Only replace
    # the qualifying-round entrant if it is the same nonzero club.
    "66 89 86 0a 0c 00 00 66 85 c0 74 3a 66 3b 86 18 0c 00 00 75 31"
    # Get the opponent from the runner-up playoff at [esi+0xc40].
    " 8b 96 40 0c 00 00 85 d2 74 27"
    " 66 3b 42 36 75 06 66 8b 4a 38 eb 0a 66 3b 42 38 75 15 66 8b 4a 36"
    # Store the opponent only if it is a different, nonzero club.
    " 66 85 c9 74 0c 66 39 c1 74 07 66 89 8e 18 0c 00 00 c3"
)

PATCHES = (
    (ROLLOVER_OFFSET, ROLLOVER_PATCH),
    (INFO_RESULT_CALL_OFFSET, INFO_RESULT_CALL_PATCH),
    (INFO_RESULT_HELPER_OFFSET, INFO_RESULT_HELPER),
    (PALETTE_REFRESH_CALL_OFFSET, PALETTE_REFRESH_CALL_PATCH),
    (PALETTE_REFRESH_HELPER_OFFSET, PALETTE_REFRESH_HELPER),
    (QUALIFIER_CALL_OFFSET, QUALIFIER_CALL_PATCH),
    (QUALIFIER_HELPER_OFFSET, QUALIFIER_HELPER)
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
