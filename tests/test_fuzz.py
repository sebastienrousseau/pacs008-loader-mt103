# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""Property-based fuzzing of ``parse_mt103``: the contract on any input.

The loader takes whatever a bank system or an agent hands it. On any text
it must either return one record whose money and date are well formed, or
raise ``ValueError`` naming what was wrong. Anything else (another
exception, an amount that is not a finite non-negative number, a date
that does not exist) is a defect, because the record goes on to become a
payment. ``fuzz/fuzz_parse_mt103.py`` holds Atheris to the same contract
in CI.
"""

from __future__ import annotations

import datetime
import math
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pacs008_loader_mt103 import parse_mt103

FUZZ = settings(max_examples=400, deadline=None)
CORPUS = Path(__file__).resolve().parent.parent / "fuzz" / "corpus"

TAGS = ["21", "23B", "32A", "50K", "50F", "52A", "52D", "57A", "59", "59F", "71A"]
YYMMDD = st.text("0123456789", min_size=6, max_size=6)
AMOUNTS = st.text("0123456789,.", min_size=1, max_size=20)
F32A = st.builds(
    lambda date, ccy, amt: f"{date}{ccy}{amt}",
    YYMMDD,
    st.sampled_from(["EUR", "USD"]),
    AMOUNTS,
)
VALUES = st.one_of(
    st.text(max_size=40),
    F32A,
    st.sampled_from(
        ["/DE89370400440532013000\nACME", "1/JOHN DOE", "DEUTDEFF", "OUR", ""]
    ),
)
FIELDS = st.builds(
    lambda ref, f32a, extra: [("20", ref), ("32A", f32a), *extra],
    st.text("ABC123", min_size=1, max_size=10),
    F32A,
    st.lists(st.tuples(st.sampled_from(TAGS), VALUES), max_size=8),
)


def _payload(fields: list[tuple[str, str]]) -> str:
    return "".join(f":{tag}:{value}\n" for tag, value in fields)


def _check(text: str) -> None:
    try:
        records = parse_mt103(text)
    except ValueError:
        return
    assert len(records) == 1, "an MT103 carries exactly one transfer"
    (record,) = records
    amount = record["interbank_settlement_amount"]
    assert isinstance(amount, float) and math.isfinite(amount), amount
    assert amount >= 0, amount
    datetime.datetime.fromisoformat(record["creation_date_time"])


@FUZZ
@given(text=st.text(max_size=400))
def test_arbitrary_text(text: str) -> None:
    _check(text)


@FUZZ
@given(fields=FIELDS)
def test_mt103_shaped_fields(fields: list[tuple[str, str]]) -> None:
    _check(_payload(fields))


@pytest.mark.parametrize("seed", sorted(p.name for p in CORPUS.iterdir()), ids=str)
def test_the_fuzz_corpus_replays(seed: str) -> None:
    """Every seed and fixed-bug input in fuzz/corpus, on every run."""
    _check((CORPUS / seed).read_text(encoding="utf-8"))
