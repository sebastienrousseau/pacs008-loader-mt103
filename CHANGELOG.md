# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
This package's version follows the [`pacs008`](https://github.com/sebastienrousseau/pacs008)
suite; a `0.0.X` release of this package targets the `0.0.X` line of `pacs008`.

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
