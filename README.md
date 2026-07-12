# pacs008-loader-mt103: MT103 → pacs.008 loader

**Convert legacy SWIFT MT103 single customer credit transfers into the
flat records that the [`pacs008`][core] library validates and turns
into ISO 20022 pacs.008 XML.** A single `parse_mt103(text)` call
returns a one-element `list[dict]` ready to feed straight into
pacs.008 generation.

> **Latest release: v0.0.1.** The first deliverable of the MT→MX
> converter project. SWIFT MT-MX coexistence for cross-border payments
> ends in **November 2025**; this loader bridges the window where
> upstream systems still emit MT103 but downstream tooling expects
> pacs.008.

## Contents

- [Overview](#overview)
- [Install](#install)
- [Quick Start](#quick-start)
- [Field Mapping](#field-mapping)
- [Assumptions and defaults](#assumptions-and-defaults)
- [Out of scope](#out-of-scope)
- [Examples](#examples)
- [Development](#development)
- [Security](#security)
- [License](#license)

## Overview

`pacs008-loader-mt103` is a small, focused companion to the
[`pacs008`][core] ISO 20022 FI-to-FI Customer Credit Transfer library.
It does one thing well: parse the mandatory + common-denominator MT103
grammar and hand back a flat record whose keys are exactly the ones
`pacs008` validates against the `pacs.008.001.08` JSON schema. The
correctness proof is that a realistic MT103 maps to a record that
passes `SchemaValidator("pacs.008.001.08").validate_batch(...)` with
zero errors.

## Install

`pacs008-loader-mt103` requires **Python 3.10+** and pulls in
`pacs008` automatically.

```bash
pip install pacs008-loader-mt103
```

## Quick Start

```python
from pacs008_loader_mt103 import parse_mt103

mt103 = """:20:REF20240712001
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

records = parse_mt103(mt103)
print(records[0]["interbank_settlement_amount"])   # 12345.67
print(records[0]["charge_bearer"])                 # SHAR

# Validate against the real pacs.008 schema:
from pacs008.validation.schema_validator import SchemaValidator
total, valid, errors = SchemaValidator("pacs.008.001.08").validate_batch(records)
assert valid == 1 and not errors
```

## Field Mapping

`parse_mt103(text: str) -> list[dict]` — an MT103 is a single transfer,
so the list always holds exactly one record.

| MT103 field | Meaning | pacs.008 key | Notes |
| :--- | :--- | :--- | :--- |
| `:20:` | Sender's Reference | `msg_id` | Also fills `end_to_end_id` when `:21:` is absent |
| `:21:` | Related Reference | `end_to_end_id` | Falls back to `:20:` |
| `:32A:` | Value Date + Currency + Amount | `creation_date_time`, `interbank_settlement_currency`, `interbank_settlement_amount` | Date → ISO datetime at midnight; amount comma-decimal → float |
| `:50A/50F/50K:` | Ordering Customer | `debtor_name` | Name from option A (BIC), F (`1/` sub-field) or K (name+address) |
| `:52A/52D:` | Ordering Institution | `debtor_agent_bic` | BIC from option A (or a BIC in option D) |
| `:57A/57D:` | Account With Institution | `creditor_agent_bic` | BIC from option A (or a BIC in option D) |
| `:59/59A/59F:` | Beneficiary Customer | `creditor_name` | Name from plain 59, option A (BIC) or F (`1/`) |
| `:71A:` | Details of Charges | `charge_bearer` | `OUR`→`DEBT`, `BEN`→`CRED`, `SHA`→`SHAR` |
| — | (synthesised) | `nb_of_txs` | Always `1` |
| — | (synthesised) | `settlement_method` | Defaults to `CLRG` |

## Assumptions and defaults

- **`settlement_method = "CLRG"`** — a bank-to-bank MT103 typically
  settles through a clearing system. Override downstream for cover
  payments (`COVE`) or correspondent-account settlement (`INDA` / `INGA`).
- **`nb_of_txs = 1`** — an MT103 carries exactly one customer transfer.
- **`creation_date_time`** — MT103 has no message timestamp, so the
  `:32A:` value date at `00:00:00` is used. Two-digit years follow the
  SWIFT sliding window (00–79 → 20YY, 80–99 → 19YY).
- **Absent optional fields are omitted, not guessed.** A schema-valid
  pacs.008 record needs the debtor agent BIC (`:52a:`), creditor agent
  BIC (`:57a:`) and charge bearer (`:71A:`); a well-formed interbank
  MT103 carries all three. When block 4 lacks an ordering / account-with
  institution, real pacs.008 generation falls back to the Sender /
  Receiver BIC in the application header (blocks 1/2) — that fallback is
  the caller's responsibility; this loader reads block 4 only.
- **Hard requirements** — only `:20:`, `:32A:` and a beneficiary
  (`:59:`/`:59A:`/`:59F:`) raise `ValueError`. Everything else is
  best-effort. The loader never crashes on unexpected input.

## Out of scope

This is the correct **core** MT103 → pacs.008 mapping, not every
optional field. Deliberately excluded in v0.0.1:

- `:33B:` instructed currency/amount and `:36:` exchange rate (FX legs).
- `:70:` remittance information and `:72:` sender-to-receiver info.
- `:23B:` / `:23E:` operation and instruction codes, `:26T:`, `:77B:`
  regulatory reporting, `:77T:` envelope contents.
- `:53a:` / `:54a:` / `:55a:` / `:56a:` correspondent and intermediary
  institutions.
- The SWIFT application header (blocks 1/2) as an agent-BIC fallback.

## Examples

Two runnable scripts live in `examples/`, exercised in CI:

- [`01_minimal_parse.py`](examples/01_minimal_parse.py) — parse and
  print the flat record.
- [`02_validate_against_pacs008.py`](examples/02_validate_against_pacs008.py)
  — parse, then validate against the real `pacs.008.001.08` schema.

## Development

```bash
git clone https://github.com/sebastienrousseau/pacs008-loader-mt103
cd pacs008-loader-mt103
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                          # 100% line + branch coverage gate
interrogate pacs008_loader_mt103  # 100% docstring gate
mypy pacs008_loader_mt103       # strict
```

## Security

`pacs008-loader-mt103` parses a flat text format with no XML envelope —
the XXE / billion-laughs surface lives upstream. Field regexes are
anchored and bounded, so catastrophic backtracking is not a concern.
See [`SECURITY.md`](SECURITY.md).

## License

Licensed under the [Apache License, Version 2.0][01]. Any contribution
submitted for inclusion shall be licensed as above, without additional
terms.

[01]: https://opensource.org/license/apache-2-0/
[core]: https://github.com/sebastienrousseau/pacs008
