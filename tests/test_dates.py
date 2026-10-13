import pytest
from app.dates import parse_date, DateParseResult

def test_iso_format():
    res = parse_date("2026-09-03", country="US")
    assert res.iso_date == "2026-09-03"
    assert not res.is_ambiguous
    assert len(res.warnings) == 0

def test_japanese_formats():
    res1 = parse_date("2026年9月3日", country="JP")
    assert res1.iso_date == "2026-09-03"
    
    res2 = parse_date("2026.09.03", country="JP")
    assert res2.iso_date == "2026-09-03"

    # Reiwa 8 = 2026 (Reiwa 1 was 2019)
    res3 = parse_date("令和8年9月3日", country="JP")
    assert res3.iso_date == "2026-09-03"

def test_textual_month_unambiguous():
    res1 = parse_date("3 Sep 2026", country="UK")
    assert res1.iso_date == "2026-09-03"
    assert not res1.is_ambiguous

    res2 = parse_date("September 3, 2026", country="US")
    assert res2.iso_date == "2026-09-03"
    assert not res2.is_ambiguous

    res3 = parse_date("3rd September 2026", country="IN")
    assert res3.iso_date == "2026-09-03"

    res4 = parse_date("03-Sep-26", country="UK")
    assert res4.iso_date == "2026-09-03"

def test_unambiguous_day_greater_than_12():
    # Day is 25, month must be 03
    res1 = parse_date("25/03/2026", country="US")
    assert res1.iso_date == "2026-03-25"
    assert not res1.is_ambiguous

    res2 = parse_date("03/25/2026", country="UK")
    assert res2.iso_date == "2026-03-25"
    assert not res2.is_ambiguous

def test_ambiguous_date_resolved_by_country():
    # 9/3/26 in US -> Sep 3, 2026
    res_us = parse_date("9/3/26", country="US")
    assert res_us.iso_date == "2026-09-03"
    assert res_us.is_ambiguous
    assert any("month-first (US vendor)" in w for w in res_us.warnings)

    # 9/3/26 in UK -> 9 March 2026
    res_uk = parse_date("9/3/26", country="UK")
    assert res_uk.iso_date == "2026-03-09"
    assert res_uk.is_ambiguous
    assert any("day-first (UK vendor)" in w for w in res_uk.warnings)

    # 03.09.2026 in DE -> 3 Sep 2026
    res_de = parse_date("03.09.2026", country="DE")
    assert res_de.iso_date == "2026-09-03"

def test_ambiguous_date_unknown_vendor_currency_fallback():
    # Unknown vendor with USD hint -> month-first
    res_usd = parse_date("09/03/2026", country="unknown", currency_hint="USD")
    assert res_usd.iso_date == "2026-09-03"
    assert res_usd.is_ambiguous
    assert any("USD hint" in w or "month-first" in w for w in res_usd.warnings)

    # Unknown vendor with EUR hint -> day-first
    res_eur = parse_date("09/03/2026", country="unknown", currency_hint="EUR")
    assert res_eur.iso_date == "2026-03-09"
    assert res_eur.is_ambiguous

def test_reject_impossible_dates():
    res = parse_date("31/02/2026", country="UK")
    assert res is None or res.iso_date is None
