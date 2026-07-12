# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2023-2026 Sebastien Rousseau. All rights reserved.

"""Tests for the pacs008-loader-mt103 loader."""

from __future__ import annotations

import pytest
from pacs008.csv.validate_csv_data import validate_csv_data
from pacs008.validation.schema_validator import SchemaValidator

from pacs008_loader_mt103 import __version__, parse_mt103

# Target ISO 20022 message type for the flat records produced here.
PACS008_MESSAGE_TYPE = "pacs.008.001.08"


def _full_mt103() -> str:
    """Return a realistic, complete MT103 covering every mapped field."""
    return (
        ":20:REF20240712001\n"
        ":23B:CRED\n"
        ":32A:260712EUR12345,67\n"
        ":50K:/DE89370400440532013000\n"
        "JOHN DOE\n"
        "123 MAIN STREET\n"
        "BERLIN\n"
        ":52A:DEUTDEFF\n"
        ":57A:CHASUS33\n"
        ":59:/GB29NWBK60161331926819\n"
        "ACME TRADING LTD\n"
        "1 CORPORATE AVENUE\n"
        "LONDON\n"
        ":70:INVOICE 998877\n"
        ":71A:SHA\n"
    )


def test_version_exposed() -> None:
    """The package exposes a non-empty semantic-style version string."""
    assert isinstance(__version__, str)
    assert __version__.count(".") >= 2


def test_full_mt103_maps_every_field() -> None:
    """A complete MT103 maps to a record with every pacs.008 field set."""
    (record,) = parse_mt103(_full_mt103())
    assert record == {
        "msg_id": "REF20240712001",
        "end_to_end_id": "REF20240712001",
        "creation_date_time": "2026-07-12T00:00:00",
        "nb_of_txs": 1,
        "settlement_method": "CLRG",
        "interbank_settlement_amount": 12345.67,
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "JOHN DOE",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "CHASUS33",
        "creditor_name": "ACME TRADING LTD",
    }


def test_record_validates_against_pacs008_schema() -> None:
    """The KEY correctness proof: the record is a schema-valid pacs.008 row.

    This runs the real :class:`SchemaValidator` for ``pacs.008.001.08`` from
    the ``pacs008`` library over the parsed record.
    """
    records = parse_mt103(_full_mt103())
    validator = SchemaValidator(PACS008_MESSAGE_TYPE)
    total, valid, errors = validator.validate_batch(records)
    assert total == 1
    assert valid == 1
    assert errors == []


def test_record_passes_pacs008_csv_validator() -> None:
    """The record also satisfies the pacs008 flat-record (CSV) validator."""
    records = parse_mt103(_full_mt103())
    assert validate_csv_data(records) is True


def test_returns_single_record_list() -> None:
    """An MT103 is one transfer, so exactly one record is returned."""
    records = parse_mt103(_full_mt103())
    assert isinstance(records, list)
    assert len(records) == 1
    assert records[0]["nb_of_txs"] == 1


@pytest.mark.parametrize(
    ("swift_code", "pacs_code"),
    [("OUR", "DEBT"), ("BEN", "CRED"), ("SHA", "SHAR")],
)
def test_charge_bearer_mapping(swift_code: str, pacs_code: str) -> None:
    """:71A: OUR/BEN/SHA map to DEBT/CRED/SHAR."""
    mt103 = _full_mt103().replace(":71A:SHA", f":71A:{swift_code}")
    (record,) = parse_mt103(mt103)
    assert record["charge_bearer"] == pacs_code


def test_unknown_charge_code_omits_charge_bearer() -> None:
    """An unrecognised :71A: code leaves charge_bearer unset (not guessed)."""
    mt103 = _full_mt103().replace(":71A:SHA", ":71A:ZZZ")
    (record,) = parse_mt103(mt103)
    assert "charge_bearer" not in record


def test_missing_charge_field_omits_charge_bearer() -> None:
    """No :71A: at all leaves charge_bearer unset."""
    mt103 = _full_mt103().replace(":71A:SHA\n", "")
    (record,) = parse_mt103(mt103)
    assert "charge_bearer" not in record


def test_swift_decimal_comma_is_parsed() -> None:
    """The SWIFT comma decimal separator becomes a float."""
    mt103 = _full_mt103().replace(":32A:260712EUR12345,67", ":32A:260712USD1000,50")
    (record,) = parse_mt103(mt103)
    assert record["interbank_settlement_amount"] == 1000.50
    assert record["interbank_settlement_currency"] == "USD"


def test_trailing_comma_amount_is_whole_number() -> None:
    """A trailing comma (no decimals) yields a whole amount."""
    mt103 = _full_mt103().replace(":32A:260712EUR12345,67", ":32A:260712EUR250,")
    (record,) = parse_mt103(mt103)
    assert record["interbank_settlement_amount"] == 250.0


def test_value_date_becomes_iso_datetime_at_midnight() -> None:
    """:32A: value date becomes an ISO datetime at 00:00:00."""
    (record,) = parse_mt103(_full_mt103())
    assert record["creation_date_time"] == "2026-07-12T00:00:00"


def test_sliding_year_window_maps_old_dates_to_1900s() -> None:
    """A YY >= 80 value date maps to the 1900s."""
    mt103 = _full_mt103().replace(":32A:260712EUR12345,67", ":32A:950712EUR100,00")
    (record,) = parse_mt103(mt103)
    assert record["creation_date_time"] == "1995-07-12T00:00:00"


def test_50k_name_extraction_skips_account_line() -> None:
    """:50K: name extraction returns the name, not the leading /account."""
    (record,) = parse_mt103(_full_mt103())
    assert record["debtor_name"] == "JOHN DOE"


def test_59_beneficiary_name_extraction() -> None:
    """:59: beneficiary name is the first line after the account line."""
    (record,) = parse_mt103(_full_mt103())
    assert record["creditor_name"] == "ACME TRADING LTD"


def test_option_f_structured_name_uses_subfield_1() -> None:
    """Option F (structured) party name is taken from the ``1/`` sub-field."""
    mt103 = (
        ":20:REF\n"
        ":32A:260712EUR100,00\n"
        ":50F:/DE89370400440532013000\n"
        "1/ALICE EXAMPLE\n"
        "2/10 DOWNING STREET\n"
        "3/GB/LONDON\n"
        ":59F:/GB29NWBK60161331926819\n"
        "1/BOB BENEFICIARY\n"
        "2/1 CORPORATE AVENUE\n"
        ":71A:OUR\n"
    )
    (record,) = parse_mt103(mt103)
    assert record["debtor_name"] == "ALICE EXAMPLE"
    assert record["creditor_name"] == "BOB BENEFICIARY"


def test_option_f_without_subfield_1_falls_back_to_first_line() -> None:
    """A structured field lacking a ``1/`` line falls back to its first line."""
    mt103 = (
        ":20:REF\n"
        ":32A:260712EUR100,00\n"
        ":59F:/GB29NWBK60161331926819\n"
        "3/GB/LONDON\n"
        ":71A:OUR\n"
    )
    (record,) = parse_mt103(mt103)
    assert record["creditor_name"] == "3/GB/LONDON"


def test_option_a_beneficiary_uses_bic_as_name() -> None:
    """Option A beneficiary (account + BIC) uses the BIC as the name."""
    mt103 = (
        ":20:REF\n"
        ":32A:260712EUR100,00\n"
        ":59A:/GB29NWBK60161331926819\n"
        "CHASUS33\n"
        ":71A:OUR\n"
    )
    (record,) = parse_mt103(mt103)
    assert record["creditor_name"] == "CHASUS33"


def test_11_char_bic_is_accepted() -> None:
    """An 11-character BIC (with branch code) is extracted intact."""
    mt103 = _full_mt103().replace(":52A:DEUTDEFF", ":52A:DEUTDEFF500")
    (record,) = parse_mt103(mt103)
    assert record["debtor_agent_bic"] == "DEUTDEFF500"


def test_option_d_institution_without_bic_omits_agent() -> None:
    """Option D (name/address) without a BIC leaves the agent BIC unset."""
    mt103 = (
        ":20:REF\n"
        ":32A:260712EUR100,00\n"
        ":52D:BANK OF SOMEWHERE\n"
        "1 BANK STREET\n"
        ":57D:ANOTHER BANK\n"
        "2 BANK ROAD\n"
        ":59:/GB29NWBK60161331926819\n"
        "ACME TRADING LTD\n"
        ":71A:OUR\n"
    )
    (record,) = parse_mt103(mt103)
    assert "debtor_agent_bic" not in record
    assert "creditor_agent_bic" not in record


def test_missing_ordering_and_account_institutions_omit_agents() -> None:
    """No :52a:/:57a: fields at all leaves both agent BICs unset."""
    mt103 = (
        ":20:REF\n"
        ":32A:260712EUR100,00\n"
        ":50K:/DE89370400440532013000\n"
        "JOHN DOE\n"
        ":59:/GB29NWBK60161331926819\n"
        "ACME TRADING LTD\n"
        ":71A:OUR\n"
    )
    (record,) = parse_mt103(mt103)
    assert "debtor_agent_bic" not in record
    assert "creditor_agent_bic" not in record


def test_ordering_customer_account_only_omits_debtor_name() -> None:
    """A :50K: with only an account line leaves debtor_name unset."""
    mt103 = (
        ":20:REF\n"
        ":32A:260712EUR100,00\n"
        ":50K:/DE89370400440532013000\n"
        ":59:/GB29NWBK60161331926819\n"
        "ACME TRADING LTD\n"
        ":71A:OUR\n"
    )
    (record,) = parse_mt103(mt103)
    assert "debtor_name" not in record


def test_related_reference_maps_to_end_to_end_id() -> None:
    """:21: Related Reference populates end_to_end_id independently of :20:."""
    mt103 = _full_mt103().replace(":23B:CRED\n", ":21:E2E-REF-9\n:23B:CRED\n")
    (record,) = parse_mt103(mt103)
    assert record["msg_id"] == "REF20240712001"
    assert record["end_to_end_id"] == "E2E-REF-9"


def test_end_to_end_id_falls_back_to_sender_reference() -> None:
    """With no :21:, end_to_end_id falls back to the :20: reference."""
    (record,) = parse_mt103(_full_mt103())
    assert record["end_to_end_id"] == record["msg_id"] == "REF20240712001"


def test_settlement_method_defaults_to_clrg() -> None:
    """settlement_method defaults to CLRG for a bank-to-bank MT103."""
    (record,) = parse_mt103(_full_mt103())
    assert record["settlement_method"] == "CLRG"


def test_raw_block4_envelope_is_unwrapped() -> None:
    """A raw ``{4:...-}`` SWIFT block-4 envelope is parsed transparently."""
    inner = _full_mt103()
    wrapped = "{1:F01DEUTDEFFAXXX0000000000}{2:I103CHASUS33XXXXN}{4:\n" + inner + "-}"
    (record,) = parse_mt103(wrapped)
    assert record["msg_id"] == "REF20240712001"
    assert record["charge_bearer"] == "SHAR"


def test_missing_sender_reference_raises() -> None:
    """A payload without :20: raises ValueError mentioning :20:."""
    mt103 = (
        ":32A:260712EUR100,00\n" ":59:/GB29NWBK60161331926819\n" "ACME TRADING LTD\n"
    )
    with pytest.raises(ValueError, match=":20:"):
        parse_mt103(mt103)


def test_empty_sender_reference_raises() -> None:
    """A :20: with an empty value raises (msg_id is required)."""
    mt103 = (
        ":20:\n"
        ":32A:260712EUR100,00\n"
        ":59:/GB29NWBK60161331926819\n"
        "ACME TRADING LTD\n"
    )
    with pytest.raises(ValueError, match=":20:"):
        parse_mt103(mt103)


def test_missing_value_date_amount_raises() -> None:
    """A payload without :32A: raises ValueError mentioning :32A:."""
    mt103 = ":20:REF\n" ":59:/GB29NWBK60161331926819\n" "ACME TRADING LTD\n"
    with pytest.raises(ValueError, match=":32A:"):
        parse_mt103(mt103)


def test_malformed_value_date_amount_raises() -> None:
    """A malformed :32A: value raises ValueError mentioning :32A:."""
    mt103 = (
        ":20:REF\n"
        ":32A:GARBAGE\n"
        ":59:/GB29NWBK60161331926819\n"
        "ACME TRADING LTD\n"
    )
    with pytest.raises(ValueError, match=":32A:"):
        parse_mt103(mt103)


def test_missing_beneficiary_raises() -> None:
    """A payload with no :59:/:59A:/:59F: raises ValueError."""
    mt103 = ":20:REF\n" ":32A:260712EUR100,00\n" ":71A:OUR\n"
    with pytest.raises(ValueError, match="beneficiary"):
        parse_mt103(mt103)


def test_beneficiary_without_name_raises() -> None:
    """A beneficiary field carrying only an account (no name) raises."""
    mt103 = (
        ":20:REF\n"
        ":32A:260712EUR100,00\n"
        ":59:/GB29NWBK60161331926819\n"
        ":71A:OUR\n"
    )
    with pytest.raises(ValueError, match="no name"):
        parse_mt103(mt103)
