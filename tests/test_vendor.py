from app.vendor import match_vendor, normalize_vendor_name, CANONICAL_VENDORS

def test_normalize_vendor_name():
    assert normalize_vendor_name("NORTHWIND TRADERS LTD") == "northwind traders"
    assert normalize_vendor_name("Blue Harbour Logistics Ltd.") == "blue harbour logistics"
    assert normalize_vendor_name("Blue Harbor Logistics Inc") == "blue harbour logistics"
    assert normalize_vendor_name("Kestrel Components Inc.") == "kestrel components"
    assert normalize_vendor_name("Meridian Industrial GmbH") == "meridian industrial"
    assert normalize_vendor_name("Sakura Precision K.K.") == "sakura precision"
    assert normalize_vendor_name("Pinecrest Packaging Pvt. Ltd.") == "pinecrest packaging"

def test_exact_and_fuzzy_vendor_matches():
    # 1. Northwind Traders (UK)
    res1 = match_vendor("NORTHWIND TRADERS LTD\n14 Quay Street, Bristol BS1 4DB, United Kingdom\nVAT No. GB 123 4567 89")
    assert res1.canonical_name == "Northwind Traders"
    assert res1.country == "UK"
    assert res1.default_currency == "GBP"
    assert res1.confidence >= 0.90

    # 2. Blue Harbour Logistics (UK)
    res2 = match_vendor("Blue Harbor Logistics Inc, Bristol UK")
    assert res2.canonical_name == "Blue Harbour Logistics"
    assert res2.country == "UK"
    assert res2.default_currency == "GBP"

    # 3. Kestrel Components (US)
    res3 = match_vendor("Kestrel Components Inc. | 880 Industrial Pkwy, Dayton OH 45402, USA")
    assert res3.canonical_name == "Kestrel Components"
    assert res3.country == "US"
    assert res3.default_currency == "USD"

    # 4. Meridian Industrial (DE)
    res4 = match_vendor("Meridan Industrial GmbH\nBerlin, Germany\nUSt-IdNr DE987654321")
    assert res4.canonical_name == "Meridian Industrial"
    assert res4.country == "DE"
    assert res4.default_currency == "EUR"

    # 5. Sakura Precision (JP)
    res5 = match_vendor("Sakura Precison KK\nTokyo, Japan\nT1234567890123")
    assert res5.canonical_name == "Sakura Precision"
    assert res5.country == "JP"
    assert res5.default_currency == "JPY"

    # 6. Pinecrest Packaging (IN)
    res6 = match_vendor("Pinecrest Packaging Pvt Ltd\nBengaluru, India\nGSTIN 29AAAAA0000A1Z5")
    assert res6.canonical_name == "Pinecrest Packaging"
    assert res6.country == "IN"
    assert res6.default_currency == "INR"

def test_bruviti_customer_exclusion():
    # Customer name Bruviti should NOT be picked as vendor
    text = "Bill To:\nBruviti Services Pvt Ltd\nFrom:\nNorthwind Traders Ltd"
    res = match_vendor(text)
    assert res.canonical_name == "Northwind Traders"
    assert res.canonical_name != "Bruviti Services Pvt Ltd"

def test_unknown_vendor():
    res = match_vendor("Acme Global Random Widgets LLC\nNowhere Land")
    assert res.canonical_name == "unknown"
    assert res.country is None
    assert res.confidence == 0.20
    assert any("Vendor name not in the canonical list." in w for w in res.warnings)
