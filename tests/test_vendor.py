import pytest
from app.vendor import match_vendor, normalize_vendor_name, CANONICAL_VENDORS

def test_normalize_vendor_name():
    assert normalize_vendor_name("Harbour Engineering Ltd.") == "harbour engineering"
    assert normalize_vendor_name("Harbor Engineering Inc") == "harbour engineering"
    assert normalize_vendor_name("Meridian Industrial GmbH") == "meridian industrial"
    assert normalize_vendor_name("Sakura Precision K.K.") == "sakura precision"
    assert normalize_vendor_name("Apex Systems Pvt. Ltd.") == "apex systems"

def test_exact_and_fuzzy_vendor_matches():
    res1 = match_vendor("Harbour Engineering Ltd\n12 Temple Way, Bristol\nVAT No GB123456789")
    assert res1.canonical_name == "Harbour Engineering Ltd"
    assert res1.country == "UK"
    assert res1.default_currency == "GBP"
    assert res1.confidence >= 0.90

    # Spelling variation: Harbor instead of Harbour
    res2 = match_vendor("Harbor Engineering Inc, Bristol UK")
    assert res2.canonical_name == "Harbour Engineering Ltd"
    assert res2.country == "UK"

    # Typo: Meridan instead of Meridian
    res3 = match_vendor("Meridan Industrial GmbH\nBerlin, Germany\nUSt-IdNr DE987654321")
    assert res3.canonical_name == "Meridian Industrial GmbH"
    assert res3.country == "DE"
    assert res3.default_currency == "EUR"

    # Typo: Sakura Precison
    res4 = match_vendor("Sakura Precison KK\nTokyo, Japan\nT1234567890123")
    assert res4.canonical_name == "Sakura Precision K.K."
    assert res4.country == "JP"
    assert res4.default_currency == "JPY"

    res5 = match_vendor("Kestrel Components Inc.\nDayton, OH, USA")
    assert res5.canonical_name == "Kestrel Components Inc."
    assert res5.country == "US"
    assert res5.default_currency == "USD"

def test_bruviti_customer_exclusion():
    # Customer name Bruviti should NOT be picked as vendor
    text = "Bill To:\nBruviti Services Pvt Ltd\nFrom:\nHarbour Engineering Ltd"
    res = match_vendor(text)
    assert res.canonical_name == "Harbour Engineering Ltd"
    assert res.canonical_name != "Bruviti Services Pvt Ltd"

def test_unknown_vendor():
    res = match_vendor("Acme Global Random Widgets LLC\nNowhere Land")
    assert res.canonical_name == "unknown"
    assert res.country is None
    assert res.confidence == 0.0
    assert any("Vendor name not in the canonical list." in w for w in res.warnings)
