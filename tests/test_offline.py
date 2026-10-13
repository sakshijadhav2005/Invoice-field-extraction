import socket
import pytest
from pathlib import Path
from app.pdf_text import extract_pdf_document
from app.fields import extract_invoice_fields

@pytest.fixture(autouse=True)
def block_external_sockets(monkeypatch):
    """
    Prevents any network socket creation to verify 100% offline functionality.
    """
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        host, port = address[0], address[1]
        # Only allow loopback if needed by local test server
        if host in ("127.0.0.1", "localhost", "::1"):
            return orig_connect(self, address)
        raise RuntimeError(f"Network access attempted to {address} during offline test!")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)

def test_offline_extraction():
    sample_pdf = Path(__file__).resolve().parent.parent / "data" / "appendix_n" / "northwind_1042.pdf"
    assert sample_pdf.exists()

    pdf_bytes = sample_pdf.read_bytes()
    doc_info = extract_pdf_document(pdf_bytes)
    resp = extract_invoice_fields(doc_info)

    assert resp.vendor == "Northwind Traders"
    assert resp.invoice_number == "NW-1042"
    assert resp.total == 433.92
