# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
This package's version follows the [`pacs008`](https://github.com/sebastienrousseau/pacs008)
suite; a `0.0.X` release of this package targets the `0.0.X` line of `pacs008`.

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

[0.0.1]: https://github.com/sebastienrousseau/pacs008-loader-mt103/releases/tag/v0.0.1
