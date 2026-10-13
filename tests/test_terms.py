from app.terms import extract_terms_days, resolve_due_date

def test_extract_net_terms():
    assert extract_terms_days("Net 30") == 30
    assert extract_terms_days("Net30") == 30
    assert extract_terms_days("N30") == 30
    assert extract_terms_days("30 days") == 30
    assert extract_terms_days("Payment within 30 days") == 30
    assert extract_terms_days("due in 14 days") == 14
    assert extract_terms_days("Terms: 45") == 45
    assert extract_terms_days("2/10 Net 30") == 30
    assert extract_terms_days("Due on receipt") is None
    assert extract_terms_days("Immediate") is None

def test_resolve_due_date_from_terms_only():
    res = resolve_due_date(
        invoice_date_iso="2026-09-03",
        printed_due_date_iso=None,
        terms_text="Net 30"
    )
    assert res.due_date_iso == "2026-10-03"
    assert any("Due date derived from terms Net 30." in w for w in res.warnings)

def test_resolve_due_date_printed_and_terms_agree():
    res = resolve_due_date(
        invoice_date_iso="2026-09-03",
        printed_due_date_iso="2026-10-03",
        terms_text="Net 30"
    )
    assert res.due_date_iso == "2026-10-03"
    assert len(res.warnings) == 0

def test_resolve_due_date_printed_and_terms_disagree():
    # Rule O1: If printed due date and terms disagree, use printed date and add warning
    res = resolve_due_date(
        invoice_date_iso="2026-09-03",
        printed_due_date_iso="2026-09-20",
        terms_text="Net 30"
    )
    assert res.due_date_iso == "2026-09-20"
    assert any("disagree" in w.lower() for w in res.warnings)

def test_resolve_due_date_due_on_receipt():
    res = resolve_due_date(
        invoice_date_iso="2026-09-03",
        printed_due_date_iso=None,
        terms_text="Due on receipt"
    )
    assert res.due_date_iso is None
    assert any("Due on receipt" in w for w in res.warnings)
