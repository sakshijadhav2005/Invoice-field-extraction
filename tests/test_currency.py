from app.currency import resolve_currency, CurrencyResult

def test_explicit_printed_currency_symbols():
    res_gbp = resolve_currency("Total: £1,234.50", vendor_currency="GBP")
    assert res_gbp.currency == "GBP"
    assert res_gbp.confidence >= 0.95
    assert len(res_gbp.warnings) == 0

    res_usd = resolve_currency("Total: $500.00", vendor_currency="USD")
    assert res_usd.currency == "USD"
    assert res_usd.confidence >= 0.95

    res_eur = resolve_currency("Gesamtbetrag: 1.200,00 €", vendor_currency="EUR")
    assert res_eur.currency == "EUR"
    assert res_eur.confidence >= 0.95

    res_jpy = resolve_currency("ご請求金額: ¥12,000", vendor_currency="JPY")
    assert res_jpy.currency == "JPY"
    assert res_jpy.confidence >= 0.95

    res_inr1 = resolve_currency("Grand Total: ₹ 1,50,000.00", vendor_currency="INR")
    assert res_inr1.currency == "INR"
    assert res_inr1.confidence >= 0.95

    res_inr2 = resolve_currency("Total Amount: Rs. 4,500.00", vendor_currency="INR")
    assert res_inr2.currency == "INR"
    assert res_inr2.confidence >= 0.95

def test_explicit_currency_codes():
    assert resolve_currency("Amount: 100 USD").currency == "USD"
    assert resolve_currency("Amount: 100 GBP").currency == "GBP"
    assert resolve_currency("Amount: 100 EUR").currency == "EUR"
    assert resolve_currency("Amount: 100 JPY").currency == "JPY"
    assert resolve_currency("Amount: 100 INR").currency == "INR"

def test_fallback_to_vendor_currency_rule_o3():
    # Rule O3: Currency not printed, fallback to vendor currency with warning & lowered confidence
    res = resolve_currency("Total: 1234.50", vendor_currency="GBP")
    assert res.currency == "GBP"
    assert res.confidence <= 0.60
    assert any("Currency not printed, vendor currency used." in w for w in res.warnings)

def test_printed_currency_conflicts_with_vendor():
    # Trust printed currency, add warning
    res = resolve_currency("Total: $1,234.50", vendor_currency="GBP")
    assert res.currency == "USD"
    assert any("Printed currency USD differs from vendor default GBP" in w for w in res.warnings)

def test_no_currency_no_vendor():
    res = resolve_currency("Total: 100.00", vendor_currency=None)
    assert res.currency is None
    assert res.confidence == 0.0
