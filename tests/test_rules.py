from app.terms import resolve_due_date
from app.amounts import parse_amount, format_amount_str
from app.currency import resolve_currency
from app.doctype import classify_document
from app.pdf_text import DocumentInfo, LineBox, WordBox
from app.fields import extract_invoice_fields

def test_rule_o1_terms_disagree_with_printed_due_date():
    # If both a printed due date and terms exist and disagree: use printed date and add warning
    res = resolve_due_date(
        invoice_date_iso="2026-09-03",
        printed_due_date_iso="2026-09-20",
        terms_text="Net 30"
    )
    assert res.due_date_iso == "2026-09-20"
    assert any("disagree" in w.lower() for w in res.warnings)

def test_rule_o1_terms_only_derives_due_date():
    # Terms only -> due_date = invoice_date + N days with warning
    res = resolve_due_date(
        invoice_date_iso="2026-09-03",
        printed_due_date_iso=None,
        terms_text="Net 30"
    )
    assert res.due_date_iso == "2026-10-03"
    assert any("Due date derived from terms Net 30." in w for w in res.warnings)

def test_rule_o2_do_not_correct_arithmetic():
    # Subtotal + tax != total: keep printed values and add warning
    lines = [
        LineBox(text="Harbour Engineering Ltd", x0=50, y0=750, x1=200, y1=765),
        LineBox(text="INVOICE", x0=50, y0=730, x1=100, y1=745),
        LineBox(text="Invoice No: INV-999", x0=50, y0=710, x1=150, y1=725),
        LineBox(text="Subtotal: £1,000.00", x0=50, y0=650, x1=200, y1=665),
        LineBox(text="VAT: £200.00", x0=50, y0=630, x1=150, y1=645),
        LineBox(text="Total: £1,500.00", x0=50, y0=610, x1=150, y1=625), # Disagrees with 1000 + 200
    ]
    doc = DocumentInfo(has_text_layer=True, full_text="\n".join(l.text for l in lines))
    doc.pages = []  # Empty pages or lines handled via full_text and lines
    
    # Run extractor with page
    from app.pdf_text import PageInfo
    doc.pages = [PageInfo(page_num=1, width=612, height=792, text=doc.full_text, lines=lines)]
    
    resp = extract_invoice_fields(doc)
    assert resp.subtotal == 1000.00
    assert resp.tax == 200.00
    assert resp.total == 1500.00  # NEVER artificially corrected to 1200.00
    assert any("Subtotal + tax ≠ total" in w for w in resp.warnings)

def test_rule_o3_currency_fallback_to_vendor_default():
    # If currency not printed on invoice, fallback to canonical vendor currency with warning & lowered confidence
    res = resolve_currency("Total Due: 1500.00", vendor_currency="GBP")
    assert res.currency == "GBP"
    assert res.confidence <= 0.60
    assert any("Currency not printed, vendor currency used." in w for w in res.warnings)

def test_rule_o4_non_invoice_document():
    # Quotation: all fields null, vendor preserved, warning naming doc type
    lines = [
        LineBox(text="Blue Harbour Logistics Ltd", x0=50, y0=750, x1=200, y1=765),
        LineBox(text="QUOTATION", x0=50, y0=730, x1=100, y1=745),
        LineBox(text="Total: £500.00", x0=50, y0=600, x1=150, y1=615),
    ]
    from app.pdf_text import PageInfo
    full_text = "\n".join(l.text for l in lines)
    doc = DocumentInfo(
        has_text_layer=True,
        full_text=full_text,
        pages=[PageInfo(page_num=1, width=612, height=792, text=full_text, lines=lines)]
    )
    resp = extract_invoice_fields(doc)
    assert resp.vendor == "Blue Harbour Logistics"
    assert resp.invoice_number is None
    assert resp.subtotal is None
    assert resp.total is None
    assert any("quotation" in w.lower() for w in resp.warnings)

def test_rule_o5_japanese_yen_formatting():
    # JPY integer parsed to 2 decimal places
    amt = parse_amount("12,000")
    assert amt == 12000.00
    assert format_amount_str(amt) == "12000.00"
