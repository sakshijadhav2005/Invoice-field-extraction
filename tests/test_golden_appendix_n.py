import json
from pathlib import Path
import pytest
from app.pdf_text import extract_pdf_document
from app.fields import extract_invoice_fields

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "appendix_n"

def test_golden_example_1():
    pdf_path = DATA_DIR / "appendix_n_example_1.pdf"
    json_path = DATA_DIR / "appendix_n_example_1.json"
    
    assert pdf_path.exists(), "Appendix N Example 1 PDF must exist"
    assert json_path.exists(), "Appendix N Example 1 JSON must exist"

    with open(json_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    doc_info = extract_pdf_document(pdf_path.read_bytes())
    actual = extract_invoice_fields(doc_info).model_dump()

    assert actual["vendor"] == expected["vendor"]
    assert actual["invoice_number"] == expected["invoice_number"]
    assert actual["invoice_date"] == expected["invoice_date"]
    assert actual["due_date"] == expected["due_date"]
    assert actual["currency"] == expected["currency"]
    assert abs(actual["subtotal"] - expected["subtotal"]) <= 0.01
    assert abs(actual["tax"] - expected["tax"]) <= 0.01
    assert abs(actual["total"] - expected["total"]) <= 0.01

def test_golden_example_2():
    pdf_path = DATA_DIR / "appendix_n_example_2.pdf"
    json_path = DATA_DIR / "appendix_n_example_2.json"

    assert pdf_path.exists(), "Appendix N Example 2 PDF must exist"
    assert json_path.exists(), "Appendix N Example 2 JSON must exist"

    with open(json_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    doc_info = extract_pdf_document(pdf_path.read_bytes())
    actual = extract_invoice_fields(doc_info).model_dump()

    assert actual["vendor"] == expected["vendor"]
    assert actual["invoice_number"] == expected["invoice_number"]
    assert actual["invoice_date"] == expected["invoice_date"]
    assert actual["due_date"] == expected["due_date"]
    assert actual["currency"] == expected["currency"]
    assert abs(actual["subtotal"] - expected["subtotal"]) <= 0.01
    assert abs(actual["tax"] - expected["tax"]) <= 0.01
    assert abs(actual["total"] - expected["total"]) <= 0.01
