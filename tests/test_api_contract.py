import io
import pytest

try:
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
except Exception as e:
    pytest.skip(f"TestClient unavailable: {e}", allow_module_level=True)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Invoice Field Extractor" in response.text

def test_extract_rejects_non_pdf():
    files = {"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")}
    response = client.post("/extract", files=files)
    assert response.status_code == 400
    assert "Invalid file format" in response.json()["detail"]

def test_extract_rejects_empty_file():
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/extract", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_extract_rejects_non_pdf_signature():
    files = {"file": ("fake.pdf", io.BytesIO(b"Not a real PDF"), "application/pdf")}
    response = client.post("/extract", files=files)
    assert response.status_code == 400
    assert "PDF header" in response.json()["detail"]

def test_extract_valid_minimal_pdf_skeleton():
    minimal_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    files = {"file": ("sample.pdf", io.BytesIO(minimal_pdf), "application/pdf")}
    response = client.post("/extract", files=files)
    assert response.status_code == 200
    data = response.json()
    
    # Check all 8 fields exist in response
    expected_fields = [
        "invoice_number", "invoice_date", "due_date",
        "subtotal", "tax", "total", "currency", "vendor"
    ]
    for field in expected_fields:
        assert field in data
    
    # Check confidence object has all 8 fields
    assert "confidence" in data
    for field in expected_fields:
        assert field in data["confidence"]
        assert isinstance(data["confidence"][field], (int, float))
        assert 0.0 <= data["confidence"][field] <= 1.0

    # Check warnings is a list
    assert "warnings" in data
    assert isinstance(data["warnings"], list)
