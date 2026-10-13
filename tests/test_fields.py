import io
from reportlab.pdfgen import canvas
from app.pdf_text import extract_pdf_document
from app.fields import extract_invoice_fields

def test_extract_fields_standard_invoice():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 780, "Blue Harbour Logistics Ltd")
    c.drawString(50, 765, "12 Temple Way, Bristol, UK")
    c.drawString(50, 750, "VAT No GB123456789")
    
    c.drawString(50, 710, "INVOICE")
    c.drawString(50, 690, "Invoice No: INV-2026-99")
    c.drawString(50, 675, "Invoice Date: 03/09/2026")
    c.drawString(50, 660, "Due Date: 03/10/2026")
    
    c.drawString(50, 600, "Subtotal: £1,000.00")
    c.drawString(50, 580, "VAT 20%: £200.00")
    c.drawString(50, 560, "Total: £1,200.00")
    c.showPage()
    c.save()
    
    doc_info = extract_pdf_document(buf.getvalue())
    resp = extract_invoice_fields(doc_info)
    
    assert resp.vendor == "Blue Harbour Logistics"
    assert resp.currency == "GBP"
    assert resp.invoice_number == "INV-2026-99"
    assert resp.invoice_date == "2026-09-03"
    assert resp.due_date == "2026-10-03"
    assert resp.subtotal == 1000.00
    assert resp.tax == 200.00
    assert resp.total == 1200.00
    assert resp.confidence.total >= 0.90
    assert any("read as day-first (UK vendor)" in w for w in resp.warnings)

def test_extract_fields_terms_only_rule_o1():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 780, "Kestrel Components Inc.")
    c.drawString(50, 765, "Dayton, Ohio, USA")
    c.drawString(50, 730, "Invoice Number: KC-5544")
    c.drawString(50, 710, "Date: 09/03/2026")
    c.drawString(50, 690, "Payment Terms: Net 30")
    c.drawString(50, 630, "Subtotal: $500.00")
    c.drawString(50, 610, "Sales Tax: $40.00")
    c.drawString(50, 590, "Total: $540.00")
    c.showPage()
    c.save()
    
    doc_info = extract_pdf_document(buf.getvalue())
    resp = extract_invoice_fields(doc_info)
    
    assert resp.vendor == "Kestrel Components"
    assert resp.currency == "USD"
    assert resp.invoice_number == "KC-5544"
    # US vendor: 09/03/2026 -> 2026-09-03
    assert resp.invoice_date == "2026-09-03"
    # Derived due date: 2026-09-03 + 30 days -> 2026-10-03
    assert resp.due_date == "2026-10-03"
    assert any("Due date derived from terms Net 30." in w for w in resp.warnings)

def test_extract_fields_arithmetic_mismatch_rule_o2():
    # If subtotal + tax != total, keep printed values and add warning
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 780, "Meridian Industrial GmbH")
    c.drawString(50, 750, "Rechnungsnr.: RE-101")
    c.drawString(50, 730, "Datum: 03.09.2026")
    c.drawString(50, 650, "Nettobetrag: 1.000,00 €")
    c.drawString(50, 630, "MwSt 19%: 190,00 €")
    c.drawString(50, 610, "Gesamtbetrag: 1.500,00 €") # deliberately doesn't match 1000 + 190
    c.showPage()
    c.save()

    doc_info = extract_pdf_document(buf.getvalue())
    resp = extract_invoice_fields(doc_info)

    assert resp.subtotal == 1000.00
    assert resp.tax == 190.00
    assert resp.total == 1500.00
    assert any("Subtotal + tax ≠ total" in w for w in resp.warnings)

def test_extract_fields_non_invoice_rule_o4():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 780, "Blue Harbour Logistics Ltd")
    c.drawString(50, 750, "QUOTATION")
    c.drawString(50, 730, "Quote #: Q-999")
    c.drawString(50, 650, "Total: £1,200.00")
    c.showPage()
    c.save()

    doc_info = extract_pdf_document(buf.getvalue())
    resp = extract_invoice_fields(doc_info)

    # All extraction fields null, vendor preserved, warning added
    assert resp.vendor == "Blue Harbour Logistics"
    assert resp.invoice_number is None
    assert resp.subtotal is None
    assert resp.total is None
    assert any("quotation" in w.lower() for w in resp.warnings)
