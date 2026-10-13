import io
import pytest
from reportlab.pdfgen import canvas
from app.pdf_text import extract_pdf_document

def test_extract_text_layer_from_reportlab_pdf():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(50, 750, "INVOICE")
    c.drawString(50, 720, "Invoice Number: INV-2026-001")
    c.drawString(50, 700, "Date: 03/09/2026")
    c.drawString(50, 680, "Vendor: Harbour Engineering Ltd")
    c.drawString(50, 650, "Subtotal: 1000.00")
    c.drawString(50, 630, "Tax: 200.00")
    c.drawString(50, 610, "Total: 1200.00")
    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()

    doc_info = extract_pdf_document(pdf_bytes)
    assert doc_info.has_text_layer
    assert "INVOICE" in doc_info.full_text
    assert "INV-2026-001" in doc_info.full_text
    assert len(doc_info.pages) == 1
    assert len(doc_info.pages[0].lines) >= 6

def test_extract_empty_or_no_text_layer():
    # Empty canvas creates a PDF with zero text
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()

    doc_info = extract_pdf_document(pdf_bytes)
    assert not doc_info.has_text_layer
    assert len(doc_info.full_text.strip()) == 0
