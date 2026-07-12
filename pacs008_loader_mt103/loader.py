# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""SWIFT MT103 -> ISO 20022 pacs.008 flat-record loader.

SWIFT MT103 is the legacy single customer credit transfer message that
correspondent banks have exchanged for decades and that ISO 20022
``pacs.008`` (FI-to-FI Customer Credit Transfer) replaces under the
CBPR+ / SWIFT MX migration (coexistence ends November 2025). This
loader bridges that gap: pass an MT103 text payload and get back the
flat record that the :mod:`pacs008` library validates and turns into
pacs.008 XML.

The MT103 grammar handled here is the mandatory + common-denominator
subset needed to populate a schema-valid pacs.008 record:

* ``:20:``  Sender's Reference        -> ``msg_id`` (+ ``end_to_end_id`` fallback)
* ``:21:``  Related Reference         -> ``end_to_end_id``
* ``:32A:`` Value Date / Ccy / Amount -> ``creation_date_time`` (date at
  midnight), ``interbank_settlement_currency``, ``interbank_settlement_amount``
* ``:50A/F/K:`` Ordering Customer      -> ``debtor_name``
* ``:52A/D:``   Ordering Institution   -> ``debtor_agent_bic``
* ``:57A/D:``   Account With Institution -> ``creditor_agent_bic``
* ``:59/A/F:``  Beneficiary Customer    -> ``creditor_name``
* ``:71A:``  Details of Charges        -> ``charge_bearer``
  (``OUR`` -> ``DEBT``, ``BEN`` -> ``CRED``, ``SHA`` -> ``SHAR``)

Two fields are synthesised because MT103 has no direct equivalent:

* ``settlement_method`` defaults to ``"CLRG"`` (settlement through a
  clearing system) -- the common case for a bank-to-bank MT103. Override
  downstream if the payment settles via correspondent accounts (``INDA`` /
  ``INGA``) or a cover message (``COVE``).
* ``nb_of_txs`` is always ``1`` -- an MT103 carries exactly one transfer.

Out of scope (deliberately -- this is the correct core mapping, not every
optional MT103 field):

* ``:33B:`` instructed currency/amount and ``:36:`` exchange rate (FX legs).
* ``:70:`` remittance information and ``:72:`` sender-to-receiver info.
* ``:23B:`` bank operation code, ``:23E:`` instruction codes, ``:26T:``,
  ``:77B:`` regulatory reporting, ``:77T:`` envelope contents.
* ``:53a:`` / ``:54a:`` / ``:55a:`` / ``:56a:`` correspondent and
  intermediary institutions.
* The SWIFT application header (blocks 1/2) -- when block 4 lacks an
  ordering / account-with institution, real pacs.008 generation falls back
  to the Sender / Receiver BIC from those headers; that fallback is the
  caller's responsibility. This loader reads block 4 only (it will unwrap a
  ``{4:...-}`` envelope if present).

A schema-valid pacs.008 record additionally requires the debtor agent BIC
(``:52a:``), creditor agent BIC (``:57a:``) and charge bearer (``:71A:``);
a well-formed interbank MT103 carries all three. When they are absent the
corresponding keys are simply omitted (the loader never crashes on
unexpected input); only ``:20:``, ``:32A:`` and the beneficiary are treated
as hard requirements that raise :class:`ValueError`.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

__all__ = ["parse_mt103"]


# --- Mapping tables ---------------------------------------------------------

# MT103 field 71A "Details of Charges" -> pacs.008 ChargeBearerType1Code.
_CHARGE_BEARER = {
    "OUR": "DEBT",  # all charges borne by the debtor
    "BEN": "CRED",  # all charges borne by the creditor
    "SHA": "SHAR",  # charges shared
}

# Default pacs.008 settlement method for a bank-to-bank MT103. Documented in
# the module docstring; callers can override for COVE / INDA / INGA.
_DEFAULT_SETTLEMENT_METHOD = "CLRG"


# --- Regex helpers ----------------------------------------------------------

# A field starts with :tag: at the beginning of a line. MT103 tags are two
# digits plus an optional single option letter (20, 21, 23B, 32A, 50K, 71A).
_FIELD_HEAD_RE = re.compile(r"^:(\d{2}[A-Z]?):", re.MULTILINE)

# :32A:260712EUR1234,56  ->  YYMMDD | CCY (3 alpha) | amount (comma-decimal)
_F32A_RE = re.compile(r"^(?P<date>\d{6})(?P<ccy>[A-Z]{3})(?P<amt>[\d.,]+)$")

# A BIC is 8 or 11 chars; this mirrors the pacs.008 schema BIC pattern so any
# line we accept as a BIC also passes downstream validation.
_BIC_RE = re.compile(r"^[A-Z0-9]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?$")

# Structured (option F) sub-field line, e.g. "1/JOHN DOE" -> number, text.
_STRUCTURED_RE = re.compile(r"^(?P<num>\d)/(?P<text>.*)$")

# The block-4 envelope of a raw SWIFT message: {4:\n...\n-}.
_BLOCK4_RE = re.compile(r"\{4:(?P<body>.*?)-\}", re.DOTALL)


# --- Tokeniser --------------------------------------------------------------


def _unwrap_block4(text: str) -> str:
    """Return the block-4 body if the payload is a raw ``{4:...-}`` envelope.

    A bare tag list (the common representation) is returned unchanged.
    """
    match = _BLOCK4_RE.search(text)
    return match.group("body") if match else text


def _iter_fields(text: str) -> Iterator[tuple[str, str]]:
    """Yield ``(tag, value)`` pairs from an MT103 payload.

    Values may span multiple lines: everything after a ``:tag:`` head up to
    (but not including) the next ``:tag:`` head is the value, with the tag
    stripped and surrounding whitespace normalised.
    """
    body = _unwrap_block4(text)
    matches = list(_FIELD_HEAD_RE.finditer(body))
    for index, match in enumerate(matches):
        tag = match.group(1)
        value_start = match.end()
        value_end = (
            matches[index + 1].start() if index + 1 < len(matches) else len(body)
        )
        value = body[value_start:value_end].strip()
        yield tag, value


# --- Field parsers ----------------------------------------------------------


def _content_lines(value: str) -> list[str]:
    """Split a party field into its content lines.

    Blank lines are dropped; a leading account line (``/account`` or
    ``//account``) is removed because it identifies the account, not the
    party name. A trailing block trailer (``-}``) is stripped defensively.
    """
    lines: list[str] = []
    for raw in value.splitlines():
        stripped = raw.strip().rstrip("}").rstrip("-").strip()
        if stripped and not stripped.startswith("/"):
            lines.append(stripped)
    return lines


def _party_name(value: str) -> str | None:
    """Extract the party name from a 50a / 59a field (options A, F, K, none).

    * Option F (structured): the name is the ``1/`` sub-field.
    * Option K / plain 59 (name + address): the name is the first line after
      the optional account line.
    * Option A (account + BIC): there is no free-text name, so the BIC line
      is returned as a best-effort identifier.

    Returns ``None`` when the field carries only an account number.
    """
    lines = _content_lines(value)
    if not lines:
        return None
    for line in lines:
        match = _STRUCTURED_RE.match(line)
        if match and match.group("num") == "1":
            return match.group("text").strip() or None
    return lines[0]


def _party_bic(value: str) -> str | None:
    """Extract a BIC from an institution field (options A and D).

    Returns the first content line that matches the BIC shape, or ``None``
    (option D typically carries a name and address, not a BIC).
    """
    for line in _content_lines(value):
        if _BIC_RE.match(line):
            return line
    return None


def _parse_amount(raw: str) -> float:
    """Convert a SWIFT amount to a float.

    SWIFT uses a comma as the decimal separator and never a thousands
    separator, so ``1234,56`` -> ``1234.56`` and a trailing comma
    (``1234,``) means a whole amount.
    """
    return float(raw.replace(",", "."))


def _parse_value_date(yymmdd: str) -> str:
    """Format a 6-char ``YYMMDD`` value date as an ISO datetime at midnight.

    Years use the SWIFT sliding window: 00-79 -> 20YY, 80-99 -> 19YY.
    """
    year = int(yymmdd[0:2])
    century = 2000 if year < 80 else 1900
    return f"{century + year:04d}-{yymmdd[2:4]}-{yymmdd[4:6]}T00:00:00"


def _parse_f32a(value: str) -> tuple[str, str, float]:
    """Parse ``:32A:`` into (creation_date_time, currency, amount)."""
    match = _F32A_RE.match(value.replace("\n", "").strip())
    if not match:
        raise ValueError(f"Malformed :32A: value date/currency/amount {value!r}")
    return (
        _parse_value_date(match.group("date")),
        match.group("ccy"),
        _parse_amount(match.group("amt")),
    )


# --- Top-level parser -------------------------------------------------------


def parse_mt103(text: str) -> list[dict[str, Any]]:
    """Parse an MT103 payload into pacs.008 flat records.

    An MT103 carries exactly one customer credit transfer, so the returned
    list always holds a single record with the keys consumed by
    :mod:`pacs008` (``msg_id``, ``creation_date_time``, ``nb_of_txs``,
    ``settlement_method``, ``end_to_end_id``, ``interbank_settlement_amount``,
    ``interbank_settlement_currency``, ``charge_bearer``, ``debtor_name``,
    ``debtor_agent_bic``, ``creditor_agent_bic``, ``creditor_name``).

    Args:
        text: The MT103 payload as a string. A raw ``{4:...-}`` block-4
            envelope, trailing whitespace and CRLF/LF differences are
            tolerated.

    Returns:
        A one-element list containing the parsed flat record. Keys whose
        source MT103 field is absent are omitted rather than guessed.

    Raises:
        ValueError: If a mandatory field is missing or malformed. The
            mandatory fields are ``:20:`` (sender's reference), ``:32A:``
            (value date / currency / amount) and a beneficiary
            (``:59:`` / ``:59A:`` / ``:59F:``). The error message names the
            offending field.
    """
    fields: dict[str, str] = {}
    for tag, value in _iter_fields(text):
        # Keep the first occurrence of each tag (MT103 fields are single).
        fields.setdefault(tag, value)

    record: dict[str, Any] = {
        "nb_of_txs": 1,
        "settlement_method": _DEFAULT_SETTLEMENT_METHOD,
    }

    # :20: Sender's Reference -> msg_id (mandatory).
    sender_ref = fields.get("20", "").strip()
    if not sender_ref:
        raise ValueError("MT103 payload missing required :20: sender's reference")
    record["msg_id"] = sender_ref

    # :21: Related Reference -> end_to_end_id, falling back to :20:.
    related_ref = fields.get("21", "").strip()
    record["end_to_end_id"] = related_ref or sender_ref

    # :32A: Value date / currency / amount (mandatory).
    if "32A" not in fields:
        raise ValueError("MT103 payload missing required :32A: value date/amount")
    creation_dt, currency, amount = _parse_f32a(fields["32A"])
    record["creation_date_time"] = creation_dt
    record["interbank_settlement_currency"] = currency
    record["interbank_settlement_amount"] = amount

    # :50a: Ordering Customer -> debtor_name.
    for tag in ("50A", "50F", "50K", "50"):
        if tag in fields:
            name = _party_name(fields[tag])
            if name:
                record["debtor_name"] = name
            break

    # :52a: Ordering Institution -> debtor_agent_bic.
    for tag in ("52A", "52D"):
        if tag in fields:
            bic = _party_bic(fields[tag])
            if bic:
                record["debtor_agent_bic"] = bic
            break

    # :57a: Account With Institution -> creditor_agent_bic.
    for tag in ("57A", "57D"):
        if tag in fields:
            bic = _party_bic(fields[tag])
            if bic:
                record["creditor_agent_bic"] = bic
            break

    # :59a: Beneficiary Customer -> creditor_name (mandatory field).
    beneficiary_tag = next((tag for tag in ("59", "59A", "59F") if tag in fields), None)
    if beneficiary_tag is None:
        raise ValueError("MT103 payload missing required beneficiary :59:/:59A:/:59F:")
    creditor_name = _party_name(fields[beneficiary_tag])
    if not creditor_name:
        raise ValueError(f"MT103 beneficiary :{beneficiary_tag}: carries no name")
    record["creditor_name"] = creditor_name

    # :71A: Details of Charges -> charge_bearer.
    charge_code = fields.get("71A", "").strip().upper()
    if charge_code in _CHARGE_BEARER:
        record["charge_bearer"] = _CHARGE_BEARER[charge_code]

    return [record]
