#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Sebastien Rousseau <sebastian.rousseau@gmail.com>
# SPDX-License-Identifier: Apache-2.0 OR MIT
"""What one MT103 costs to parse, and why there is no batch axis.

An MT103 carries **exactly one** customer credit transfer. `parse_mt103`
says so, and returns a one-element list to match. That single fact
decides the shape of this benchmark, and it is worth being explicit about
because the obvious benchmark for a loader -- throughput as the input
grows -- measures nothing here.

Concatenating two MT103s and parsing the result returns **one** record,
silently. The second message is not rejected and no error is raised; it
is simply not there. A "scaling" curve built that way shows the
per-message cost falling as the input grows, which looks like excellent
batching and is the opposite: the cost falls because it is being divided
by messages that were never parsed.

So a migration that reads a file of MT103s has to split it into messages
itself and call this once per message. What matters then is the cost of
that one call, which is what this measures:

* **A complete message**, every mapped field present.
* **The block-4 envelope** form, ``{4:...-}``, which real SWIFT traffic
  arrives in and which costs a little more to unwrap.
* **The rejection path.** A migration meets malformed messages -- that
  is most of why it is being done -- so how fast a bad message is
  refused is a real number, not a curiosity. Here it is *cheaper* than
  success: the mandatory-field check fails before the field parsers run.

Run::

    python benches/bench_parse_mt103.py
    python benches/bench_parse_mt103.py --json
    python benches/bench_parse_mt103.py --quick     # what CI runs

Nothing here asserts a threshold: wall-clock is not comparable between
machines, and a flaky performance gate teaches people to ignore red. CI
runs ``--quick`` so a benchmark that has stopped compiling against the
current API fails the build instead of rotting into a file that reads as
verified and is not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pacs008_loader_mt103 import parse_mt103  # noqa: E402


def message(index: int = 0) -> str:
    """A complete MT103 covering every mapped field."""
    return (
        f":20:REF{index:012d}\n"
        ":23B:CRED\n"
        f":32A:260712EUR{(index % 9000) + 100},67\n"
        ":50K:/DE89370400440532013000\n"
        f"JOHN DOE {index}\n"
        "123 MAIN STREET\n"
        "BERLIN\n"
        ":52A:DEUTDEFF\n"
        ":57A:CHASUS33\n"
        ":59:/GB29NWBK60161331926819\n"
        f"ACME TRADING LTD {index}\n"
        "1 CORPORATE AVENUE\n"
        "LONDON\n"
        f":70:INVOICE {index}\n"
        ":71A:SHA\n"
    )


def enveloped(index: int = 0) -> str:
    """The same message inside a raw SWIFT block-4 envelope."""
    return "{4:\n" + message(index) + "-}"


def malformed(index: int = 0) -> str:
    """The same message with its mandatory ``:32A:`` field corrupted."""
    return message(index).replace(":32A:", ":32X:")


def _best(call, repeats: int) -> float:
    """Best-of timing after one untimed warm-up.

    The minimum is the least noisy estimator available; the mean follows
    whatever else the machine is doing.
    """
    call()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return min(samples)


def _refuse(text: str):
    """Parse expecting refusal. A rejection is a result, and it is timed."""

    def wrapped():
        try:
            return parse_mt103(text)
        except ValueError:
            return None

    return wrapped


def concatenation_check() -> dict:
    """Evidence for the claim that a second message is dropped.

    Measured rather than asserted in prose: if the loader ever grows
    multi-message support this turns from a documented limitation into a
    stale warning, and the benchmark should be the thing that notices.
    """
    pair = message(0) + message(1)
    records = parse_mt103(pair)
    return {
        "records_returned": len(records),
        "first_msg_id": records[0].get("msg_id") if records else None,
        "second_dropped": len(records) == 1,
    }


def run(quick: bool) -> dict:
    repeats = 200 if quick else 5_000
    plain, block, bad = message(), enveloped(), malformed()
    cases = {
        "complete message": _best(lambda: parse_mt103(plain), repeats),
        "block-4 envelope": _best(lambda: parse_mt103(block), repeats),
        "rejected (bad :32A:)": _best(_refuse(bad), repeats),
    }
    return {
        "cases_us": {name: seconds * 1e6 for name, seconds in cases.items()},
        "messages_per_second": (
            1.0 / cases["complete message"] if cases["complete message"] else 0.0
        ),
        "concatenation": concatenation_check(),
    }


def render(results: dict) -> None:
    print("  Cost of one call:\n")
    for name, micros in results["cases_us"].items():
        print(f"    {name:<24}{micros:>9.2f} us")

    plain = results["cases_us"]["complete message"]
    bad = results["cases_us"]["rejected (bad :32A:)"]
    if bad < plain:
        print(
            f"\n    Refusal is cheaper than success ({bad:.2f} against "
            f"{plain:.2f} us): the mandatory-field\n    check fails before "
            f"the field parsers run. A migration meets plenty of malformed\n"
            f"    messages, so that is the right way round."
        )
    print(
        f"\n  Throughput: {results['messages_per_second']:,.0f} messages/sec, "
        f"one call per message."
    )

    check = results["concatenation"]
    if check["second_dropped"]:
        print(
            "\n  There is no batch axis, and this is why: parsing two "
            "concatenated MT103s returns\n  "
            f"{check['records_returned']} record "
            f"({check['first_msg_id']}). The second is dropped silently -- "
            "not rejected,\n  not reported. An MT103 carries exactly one "
            "credit transfer, so a migration reading a\n  file has to split "
            "it into messages itself and call this once per message.\n\n"
            "  A throughput curve built on concatenated input would show "
            "per-message cost falling\n  as the file grows. That is not "
            "batching; it is dividing by messages never parsed."
        )
    else:
        print(
            "\n  Parsing concatenated messages now returns "
            f"{check['records_returned']} records -- the loader has grown "
            "multi-message\n  support and this benchmark's framing needs "
            "revisiting."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--quick", action="store_true", help="fewer repeats, as CI runs"
    )
    args = parser.parse_args()

    results = run(quick=args.quick)
    if args.json:
        json.dump(results, sys.stdout, indent=1)
        print()
    else:
        render(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
