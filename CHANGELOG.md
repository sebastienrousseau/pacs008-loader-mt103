# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
This package's version follows the [`pacs008`](https://github.com/sebastienrousseau/pacs008)
suite; a `0.0.X` release of this package targets the `0.0.X` line of `pacs008`.

## [Unreleased]

### Security

- `requirements/audit.txt`, the CI audit job's pip-audit environment, is
  compiled for Python 3.12, the only Python that installs it, and floors
  `filelock` at `>=4.2.1` (GHSA-9vhv-jxww-xfm5, GHSA-567q-5qvw-pf92,
  GHSA-v4x8-3wr5-3wq8). The Python 3.10 split had pinned `filelock 4.1.0`;
  4.2.1 needs Python 3.11.

### Removed

- Python 3.10 is no longer supported: `requires-python` is `>=3.11`, in
  step with the `pacs008` core, as 3.10 reaches end of life in October
  2026. The 3.10 classifier goes, CI tests 3.11 to 3.14, and ruff and
  mypy target 3.11. The `tomli` fallback in
  `scripts/check_suite_consistency.py` goes, with `tomli` in
  `requirements/lint.in` and `test.in`. `make pip-compile` compiles for
  3.11, so `build.txt`, `complexity.txt`, `lint.txt`, `runtime.txt` and
  `test.txt` lose their 3.10-only lines (exceptiongroup, tomli,
  importlib-metadata 9.0.1, more-itertools 11.1.0, typing-extensions,
  and the older coverage, hypothesis, pycparser, rpds-py, starlette and
  websockets pins); no other pin moves.

## [0.0.15] - 2026-10-23

Released in lockstep with `pacs008` 0.0.15, the suite's convergence
release. This package skips 0.0.13 and 0.0.14, which `pacs008-mcp`
published alone. Parser fixes change what `parse_mt103` accepts for
`:32A:`; everything else is supply chain and CI.

### Security

- **An unterminated block-4 opener no longer costs quadratic time**
  (CWE-1333). `parse_mt103` found the `{4:...-}` envelope with a lazy
  regular expression, so each `{4:` without a closing `-}` made the
  search scan to the end of the text again: 60 KB of `{4:` took about
  6.5 seconds before the input was rejected. The envelope is now found
  in one pass, with the same result on every input. Every release up to
  0.0.12 is affected.

### Fixed

- `:32A:` value dates that do not exist are rejected with a `ValueError`
  naming `:32A:`. `000000` used to come back as `2000-00-00` and
  `260230` as `2026-02-30`.
- `:32A:` amounts outside the SWIFT form are rejected with a
  `ValueError` naming `:32A:`. **Behaviour change:** an amount with a
  dot (`EUR1.234`, `EUR1000.50`) used to be read as a decimal point and
  is now refused, because SWIFT amounts never carry one; `1,2,3` and a
  bare `,` now raise the documented error instead of float's own; an
  amount over 15 characters (SWIFT `15d`), which could become an
  infinite amount, is refused.
- The README's latest-release callout said v0.0.3 through 0.0.12.

### Changed

- `pacs008 >= 0.0.15, < 1` (was `>= 0.0.7`), in `pyproject.toml` and
  every `requirements/*.in`.
- Every CI install is hash-pinned from `requirements/*.txt`, compiled by
  `uv` (`make pip-compile`), and every action is pinned by commit SHA.
  The release build runs with `--no-isolation` from the pinned build
  tree. `certifi` is floored at 2026.10.19 (GHSA-6q48-6c7w-9gw2) in
  every tree that resolves it.
- New CI gates: CodeQL (security-and-quality), OpenSSF Scorecard, DCO,
  `pip-audit` over every requirements file, complexity ceilings against
  `complexity-baseline.json` (one offender, `parse_mt103`), Atheris
  fuzzing (`fuzz/`) and Hypothesis fuzzing in the test suite, mypy
  `--strict` over `scripts/`, and `scripts/verify_versions.py`
  ("Version sources agree").
- Releases attach SLSA build provenance, sigstore signatures and
  CycloneDX and SPDX SBOMs, and publish with PEP 740 attestations.
- The Makefile runs what CI runs; `make check` is the full gate.

## [0.0.12] - 2026-08-29

Aligns the `pacs008` suite on one version number, and adds the gates this
repository was missing.

### Added

- `benches/bench_parse_mt103.py`. It measures the cost of one call and
  documents why there is no batch axis: concatenating two MT103s returns
  one record, the second dropped silently, so a throughput curve built
  that way would divide by messages never parsed. The benchmark asserts
  that rather than only describing it.
- `docs/benchmarks.md` and `CONTRIBUTING.md`.
- `scripts/check_suite_consistency.py` and a scheduled `Suite
  Consistency` workflow comparing this tree, and every published member,
  against PyPI.
- `tests/test_suite_conformance.py`, the shared suite conformance gate.
- **A formatter.** This repository linted with `ruff check` but never
  formatted, which the conformance gate correctly refuses. `ruff format
  --check` now runs in CI; three files were normalised by it.

### Changed

- Version aligned to `0.0.12` across `pacs008`, `pacs008-mcp` and
  `pacs008-loader-mt103`, which had drifted to `0.0.11`, `0.0.9` and
  `0.0.3`.
- `SECURITY.md`'s supported-version table follows the bump.

## [0.0.3] - 2026-07-26

### Added

- **PEP 561 `py.typed` marker** (`pacs008_loader_mt103/py.typed`). The
  package is `mypy --strict` clean but previously shipped no marker, so
  downstream consumers received none of its annotations. The marker is
  included in the built wheel by the Hatchling backend and verified present.
- **Regression test** (`tests/test_py_typed_marker.py`) that fails before a
  release ships if the marker is dropped from the package.

### Changed

- Version `0.0.2` → `0.0.3`; `SECURITY.md` supported-versions reconciled.

## [0.0.2] - 2026-07-18

### Changed

- chore(deps): require `pacs008>=0.0.7` (was `>=0.0.5`) to pick up the
  0.0.7 validation bug fix. No API changes in this loader.

## [0.0.1] - 2026-07-12

### Added

First release of `pacs008-loader-mt103`, a SWIFT MT103 → ISO 20022
pacs.008 converter and the first deliverable of the MT→MX converter
project. Companion to the
[`pacs008`](https://github.com/sebastienrousseau/pacs008) core library.

Public API: a single function `parse_mt103(text)` that returns a
one-element `list[dict]` whose keys are exactly the flat-record fields
`pacs008` validates against the `pacs.008.001.08` JSON schema, so the
records feed straight into pacs.008 generation.

#### Mapped MT103 fields

- `:20:` Sender's Reference → `msg_id` (+ `end_to_end_id` fallback)
- `:21:` Related Reference → `end_to_end_id`
- `:32A:` Value Date / Currency / Amount → `creation_date_time`
  (date at midnight), `interbank_settlement_currency`,
  `interbank_settlement_amount` (SWIFT comma-decimal handled)
- `:50A/50F/50K:` Ordering Customer → `debtor_name`
- `:52A/52D:` Ordering Institution → `debtor_agent_bic`
- `:57A/57D:` Account With Institution → `creditor_agent_bic`
- `:59/59A/59F:` Beneficiary Customer → `creditor_name`
- `:71A:` Details of Charges → `charge_bearer`
  (`OUR`→`DEBT`, `BEN`→`CRED`, `SHA`→`SHAR`)
- Synthesised: `nb_of_txs` = `1`, `settlement_method` = `CLRG`

#### Quality gates

- 100% line + branch coverage enforced via `--cov-fail-under=100`.
- 100% docstring coverage enforced via `interrogate`.
- Type-checked with `mypy --strict`; linted with `ruff`; formatted
  with `black`.
- A parsed record is verified schema-valid against the real
  `pacs008` `SchemaValidator("pacs.008.001.08")` in the test suite.

[0.0.3]: https://github.com/sebastienrousseau/pacs008-loader-mt103/releases/tag/v0.0.3
[0.0.2]: https://github.com/sebastienrousseau/pacs008-loader-mt103/releases/tag/v0.0.2
[0.0.1]: https://github.com/sebastienrousseau/pacs008-loader-mt103/releases/tag/v0.0.1
