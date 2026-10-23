# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Coverage-guided fuzzing of ``parse_mt103`` with Atheris.

The contract, the same one ``tests/test_fuzz.py`` checks with Hypothesis:
on any text the loader returns one record whose amount is a finite,
non-negative number and whose value date exists, or raises ``ValueError``.
Any other exception, or a malformed amount or date in the record, is a
crash that libFuzzer reports and minimises.

An input that starts with ``:`` or ``{`` is parsed as MT103 text as it
stands, so the files in ``fuzz/corpus/`` (real-shaped messages and the
inputs of fixed bugs) are seeds and regression cases at once. Any other
input is decoded into a sequence of MT103 fields.

Run (Linux x86_64, Python 3.12 to 3.14)::

    pip install --require-hashes -r requirements/fuzz.txt
    pip install --no-deps -e .
    python fuzz/fuzz_parse_mt103.py fuzz/corpus -max_total_time=60
"""

import datetime
import math
import sys

import atheris

with atheris.instrument_imports():
    from pacs008_loader_mt103 import parse_mt103

TAGS = ["20", "21", "23B", "32A", "50K", "50F", "52A", "57A", "59", "59F", "71A"]


def _text(data: bytes) -> str:
    """The MT103 payload this input encodes."""
    if data[:1] in (b":", b"{"):
        return data.decode("utf-8", "replace")
    fdp = atheris.FuzzedDataProvider(data)
    fields = [
        f":{fdp.PickValueInList(TAGS)}:{fdp.ConsumeUnicodeNoSurrogates(48)}"
        for _ in range(fdp.ConsumeIntInRange(0, 16))
    ]
    return "\n".join(fields)


def test_one_input(data: bytes) -> None:
    """Parse one input and hold the record to the contract."""
    try:
        records = parse_mt103(_text(data))
    except ValueError:
        return
    if len(records) != 1:
        raise AssertionError(f"expected one record, got {len(records)}")
    record = records[0]
    amount = record["interbank_settlement_amount"]
    if not (math.isfinite(amount) and amount >= 0):
        raise AssertionError(f"amount out of range: {amount!r}")
    try:
        datetime.datetime.fromisoformat(record["creation_date_time"])
    except ValueError as exc:
        raise AssertionError(f"impossible date in output: {exc}") from exc


def main() -> None:
    """Hand the harness to libFuzzer."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
