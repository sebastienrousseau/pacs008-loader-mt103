# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Parse an MT103 and validate the record against the real pacs.008 schema.

This proves the round trip: MT103 text in, a schema-valid ``pacs.008.001.08``
flat record out, verified by the ``pacs008`` library's ``SchemaValidator``.

Run with ``python examples/02_validate_against_pacs008.py``.
"""

from pacs008.validation.schema_validator import SchemaValidator

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
    """Parse the demo MT103 and validate it against pacs.008.001.08."""
    records = parse_mt103(MT103)
    validator = SchemaValidator("pacs.008.001.08")
    total, valid, errors = validator.validate_batch(records)
    print(f"records: {total}  valid: {valid}")
    if errors:
        for index, row_errors in errors:
            for error in row_errors:
                print(f"  row {index}: {error}")
    else:
        print("All records are schema-valid pacs.008.001.08. ✅")


if __name__ == "__main__":
    main()
