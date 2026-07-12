# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Minimal example: parse an MT103 payload and inspect the flat record.

Run with ``python examples/01_minimal_parse.py``.
"""

from pacs008_loader_mt103 import parse_mt103

MT103 = """:20:REF20240712001
:23B:CRED
:32A:260712EUR12345,67
:50K:/DE89370400440532013000
JOHN DOE
123 MAIN STREET
BERLIN
:52A:DEUTDEFF
:57A:CHASUS33
:59:/GB29NWBK60161331926819
ACME TRADING LTD
1 CORPORATE AVENUE
LONDON
:70:INVOICE 998877
:71A:SHA
"""


def main() -> None:
    """Parse the demo MT103 and print the resulting pacs.008 record."""
    (record,) = parse_mt103(MT103)
    for key, value in record.items():
        print(f"{key:32}: {value!r}")


if __name__ == "__main__":
    main()
