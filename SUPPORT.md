<!-- SPDX-License-Identifier: Apache-2.0 -->

# Getting support

Thanks for using `pacs008-loader-mt103`. Here's the fastest way to get
help, by need.

## Read first

- **[README.md](README.md)** — install, quick start, the full MT103 →
  pacs.008 field-mapping table, assumptions and out-of-scope fields.
- **[`examples/`](examples/)** — two runnable scripts exercised in CI.

## Questions & how-to

Open a [GitHub Discussion](https://github.com/sebastienrousseau/pacs008-loader-mt103/discussions)
with:

- Python version + OS
- `pacs008-loader-mt103` version + `pacs008` version
- A minimal MT103 payload that reproduces the issue (sensitive values
  redacted)
- The full error output

## Bugs

Open an [issue](https://github.com/sebastienrousseau/pacs008-loader-mt103/issues/new)
with the same triage data plus expected vs. actual behaviour.

## Feature requests

Likely categories, all out of scope for v0.0.1:

- **FX legs** (`:33B:` instructed amount, `:36:` exchange rate).
- **Remittance / sender-to-receiver info** (`:70:`, `:72:`).
- **Correspondent / intermediary institutions** (`:53a:`–`:56a:`).
- **Application-header agent fallback** (blocks 1/2 Sender / Receiver
  BIC when `:52a:` / `:57a:` are absent).

## Security

**Do not** open public issues for vulnerabilities. Follow the private
disclosure process in [SECURITY.md](SECURITY.md).

## Supported versions

| Version | Supported? |
| :--- | :--- |
| 0.0.2 (latest) | ✅ |

Requires Python 3.10+ and `pacs008 >= 0.0.7`.
