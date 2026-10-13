from app.amounts import parse_amount, format_amount_str

def test_standard_us_uk_amounts():
    assert parse_amount("1,234.56") == 1234.56
    assert parse_amount("$1,234.56") == 1234.56
    assert parse_amount("1234.50") == 1234.50
    assert parse_amount("45.00") == 45.00

def test_german_european_amounts():
    assert parse_amount("1.234,56") == 1234.56
    assert parse_amount("1.234,56 €") == 1234.56
    assert parse_amount("123,45") == 123.45

def test_indian_amounts():
    assert parse_amount("1,23,456.00") == 123456.00
    assert parse_amount("₹ 1,23,456.50") == 123456.50
    assert parse_amount("Rs. 50,000.00") == 50000.00

def test_japanese_yen_amounts():
    # Rule O5: JPY with no decimals or with comma
    assert parse_amount("12,000") == 12000.00
    assert parse_amount("¥12,000") == 12000.00
    assert parse_amount("12000") == 12000.00

def test_percentage_rejection():
    # Never confuse a percentage like 20% or 7.25% with an amount
    assert parse_amount("20%") is None
    assert parse_amount("7.25%") is None
    assert parse_amount("18.0 %") is None

def test_space_and_apostrophe_separators():
    assert parse_amount("1 234,56") == 1234.56
    assert parse_amount("1'234.56") == 1234.56

def test_negative_amounts():
    assert parse_amount("-150.00") == -150.00
    assert parse_amount("(150.00)") == -150.00
    assert parse_amount("150.00-") == -150.00

def test_format_amount_str():
    assert format_amount_str(1234.56) == "1234.56"
    assert format_amount_str(12000.0) == "12000.00"
