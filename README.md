# Bruviti Invoice Field Extractor

High-performance, offline-first invoice field extraction service built for **Use Case 3 — Invoice field extraction (Bruviti Campus Drive 2026)**.

The system extracts key invoice metadata from digital PDFs with text layers using PyMuPDF bounding-box geometry, locale-aware parsing, fuzzy canonical vendor resolution, and candidate scoring. It runs entirely offline without cloud dependencies, external OCR, or heavyweight neural models.

---

## 1. Quick Start (One Command)

### Prerequisites
- **Python 3.11+** installed and available in PATH.

### Run on Linux / macOS
```bash
chmod +x run.sh
./run.sh
```

### Run on Windows
```cmd
run.bat
```

The script automatically:
1. Creates a virtual environment in `venv/` if not present.
2. Installs pinned dependencies from `requirements.txt`.
3. Starts the FastAPI server on `http://0.0.0.0:8000`.

---

## 2. Service Endpoints

Once the server is running on port 8000:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web UI (vanilla HTML/CSS/JS upload form & JSON viewer) |
| `GET` | `/health` | Health check endpoint returning `{"status": "ok"}` |
| `POST` | `/extract` | Multipart upload (`file`) extracting the 8 invoice fields |

### Example cURL Request
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "accept: application/json" \
  -F "file=@data/appendix_n/northwind_1042.pdf"
```

### Response Schema (Example 1: Northwind Traders)
```json
{
  "vendor": "Northwind Traders",
  "invoice_number": "NW-1042",
  "invoice_date": "2026-09-03",
  "due_date": "2026-10-03",
  "currency": "GBP",
  "subtotal": 361.6,
  "tax": 72.32,
  "total": 433.92,
  "confidence": {
    "vendor": 0.98,
    "invoice_number": 0.95,
    "invoice_date": 0.9,
    "due_date": 0.9,
    "currency": 0.95,
    "subtotal": 0.97,
    "tax": 0.97,
    "total": 0.97
  },
  "warnings": []
}
```

---

## 3. Running Tests & Benchmarks

Run the complete test suite (unit tests, golden tests, business rules, API contract, offline verification, and latency benchmarks):
```bash
pytest -s
```

All 58 tests pass in under 7 seconds.

### Latency Performance
```
[Performance Benchmark (50 files)]
Mean Latency: ~14.5 ms
P95 Latency:  ~18.7 ms (Limit: 1000 ms)
Max Latency:  ~19.4 ms
```

---

## 4. Dataset Generation & Evaluation

To regenerate synthetic invoices, held-out sets, and Appendix N reference PDFs:
```bash
python scripts/make_data.py
```

To run the accuracy evaluation report across all datasets:
```bash
python scripts/eval.py --all
```

Options:
- `python scripts/eval.py` : Evaluates synthetic dev set (150 files).
- `python scripts/eval.py --holdout` : Evaluates held-out validation set (35 files).
- `python scripts/eval.py --appendix` : Evaluates Appendix N reference invoices (3 files).
- `python scripts/eval.py --all` : Evaluates all datasets.

---

## 5. Repository Structure

```
.
├── app/
│   ├── main.py            # FastAPI service, static mounting, error handling
│   ├── schema.py          # Pydantic response models
│   ├── pdf_text.py        # PyMuPDF line extraction & bounding box clustering
│   ├── vendor.py          # Canonical vendor matching & typo tolerance (Rapidfuzz)
│   ├── doctype.py         # Document type classification (Rule O4)
│   ├── currency.py        # Symbol & code resolution + vendor fallback (Rule O3)
│   ├── dates.py           # Multi-locale date parsing & ambiguity resolution
│   ├── terms.py           # Payment terms parser & due date resolver (Rule O1)
│   ├── amounts.py         # Multi-locale number normalizer & JPY format (Rule O5)
│   └── fields.py          # Candidate scoring & arithmetic cross-checks (Rule O2)
├── static/
│   └── index.html         # Zero-dependency vanilla web interface
├── data/
│   ├── appendix_n/        # Appendix N reference invoices & ground truth
│   ├── synthetic/         # 150 synthetic dev invoices & ground truth
│   └── handmade/          # 35 held-out validation invoices
├── scripts/
│   ├── make_data.py       # Deterministic dataset generation script
│   └── eval.py            # Accuracy evaluation reporting tool
├── tests/                 # 58 automated pytest tests
├── requirements.txt       # Pinned dependencies
├── run.sh                 # Linux/macOS launcher
├── run.bat                # Windows launcher
├── DATA.md                # Dataset creation, splits, and error analysis
├── NOTES.md               # Technical decisions and business rules documentation
└── AI.md                  # Attribution of AI assistance
```
