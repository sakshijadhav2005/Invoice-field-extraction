import time
import statistics
from pathlib import Path
import pytest
from app.pdf_text import extract_pdf_document
from app.fields import extract_invoice_fields

def test_performance_p95_under_1_second():
    """
    Measures extraction latency across 50 invoice PDFs.
    Verifies that p95 latency is strictly under 1.0 second (target < 300ms).
    """
    synth_dir = Path(__file__).resolve().parent.parent / "data" / "synthetic"
    pdf_files = sorted(list(synth_dir.glob("*.pdf")))[:50]
    
    assert len(pdf_files) >= 50, f"Expected at least 50 synthetic invoices, found {len(pdf_files)}"

    latencies = []

    # Warm-up run on first file
    warm_bytes = pdf_files[0].read_bytes()
    extract_invoice_fields(extract_pdf_document(warm_bytes))

    for pdf_path in pdf_files:
        pdf_bytes = pdf_path.read_bytes()
        t0 = time.perf_counter()
        doc_info = extract_pdf_document(pdf_bytes)
        resp = extract_invoice_fields(doc_info)
        duration = time.perf_counter() - t0
        latencies.append(duration)
        assert resp.vendor is not None

    latencies.sort()
    # 95th percentile index: index 47 out of 50
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_idx]
    mean_latency = statistics.mean(latencies)
    max_latency = max(latencies)

    print(f"\n[Performance Benchmark (50 files)]")
    print(f"Mean Latency: {mean_latency * 1000:.2f} ms")
    print(f"P95 Latency:  {p95_latency * 1000:.2f} ms")
    print(f"Max Latency:  {max_latency * 1000:.2f} ms")

    # Hard requirement: p95 under 1.0 second (1000 ms)
    assert p95_latency < 1.0, f"P95 latency {p95_latency:.3f}s exceeds 1.0s limit"
