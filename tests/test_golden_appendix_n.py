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

    # Check Appendix N warnings for Example 2
    assert any("month-first (US vendor)" in w for w in actual["warnings"])
    assert any("Due date derived from terms Net 30" in w for w in actual["warnings"])

def test_golden_example_3():
    pdf_path = DATA_DIR / "appendix_n_example_3.pdf"
    json_path = DATA_DIR / "appendix_n_example_3.json"

    assert pdf_path.exists(), "Appendix N Example 3 PDF must exist"
    assert json_path.exists(), "Appendix N Example 3 JSON must exist"

    with open(json_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    doc_info = extract_pdf_document(pdf_path.read_bytes())
    actual = extract_invoice_fields(doc_info).model_dump()

    assert actual["vendor"] == expected["vendor"]
    assert actual["invoice_number"] == expected["invoice_number"]
    assert actual["invoice_date"] == expected["invoice_date"]
    assert actual["due_date"] is None
    assert actual["currency"] == expected["currency"]
    assert abs(actual["subtotal"] - expected["subtotal"]) <= 0.01
    assert abs(actual["tax"] - expected["tax"]) <= 0.01
    assert abs(actual["total"] - expected["total"]) <= 0.01

    # Check Appendix N warnings for Example 3
    assert any("Vendor name not in the canonical list" in w for w in actual["warnings"])
    assert any("No due date or payment terms found" in w for w in actual["warnings"])

def test_golden_northwind_1042():
    pdf_path = DATA_DIR / "northwind_1042.pdf"
    assert pdf_path.exists()
    doc_info = extract_pdf_document(pdf_path.read_bytes())
    actual = extract_invoice_fields(doc_info).model_dump()

    assert actual["vendor"] == "Northwind Traders"
    assert actual["invoice_number"] == "NW-1042"
    assert actual["invoice_date"] == "2026-09-03"
    assert actual["due_date"] == "2026-10-03"
    assert actual["currency"] == "GBP"
    assert abs(actual["subtotal"] - 361.60) <= 0.01
    assert abs(actual["tax"] - 72.32) <= 0.01
    assert abs(actual["total"] - 433.92) <= 0.01

def test_golden_kestrel_0311():
    pdf_path = DATA_DIR / "kestrel_0311.pdf"
    assert pdf_path.exists()
    doc_info = extract_pdf_document(pdf_path.read_bytes())
    actual = extract_invoice_fields(doc_info).model_dump()

    assert actual["vendor"] == "Kestrel Components"
    assert actual["invoice_number"] == "KC-0311"
    assert actual["invoice_date"] == "2026-09-03"
    assert actual["due_date"] == "2026-10-03"
    assert actual["currency"] == "USD"
    assert abs(actual["subtotal"] - 225.80) <= 0.01
    assert abs(actual["tax"] - 16.37) <= 0.01
    assert abs(actual["total"] - 242.17) <= 0.01
    assert any("month-first (US vendor)" in w for w in actual["warnings"])
    assert any("Due date derived from terms Net 30" in w for w in actual["warnings"])

def test_golden_unknown_vendor():
    pdf_path = DATA_DIR / "unknown_vendor.pdf"
    assert pdf_path.exists()
    doc_info = extract_pdf_document(pdf_path.read_bytes())
    actual = extract_invoice_fields(doc_info).model_dump()

    assert actual["vendor"] == "unknown"
    assert actual["invoice_number"] == "7781"
    assert actual["invoice_date"] == "2026-08-21"
    assert actual["due_date"] is None
    assert actual["currency"] == "INR"
    assert abs(actual["subtotal"] - 12000.00) <= 0.01
    assert abs(actual["tax"] - 2160.00) <= 0.01
    assert abs(actual["total"] - 14160.00) <= 0.01
    assert actual["confidence"]["vendor"] == 0.20
    assert any("Vendor name not in the canonical list" in w for w in actual["warnings"])
    assert any("No due date or payment terms found" in w for w in actual["warnings"])

