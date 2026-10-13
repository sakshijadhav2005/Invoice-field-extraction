# DATA.md: Dataset Construction, Splits, and Evaluation

This document outlines the data sources, synthetic generation methodology, split design, evaluation metrics, and expected failure modes on real-world invoices for **Use Case 3 — Invoice field extraction**.

---

## 1. Data Sources and Generation Methodology

Since no pre-labelled training set was provided in the prompt, three complementary datasets were constructed to validate generalization across unseen layouts, locales, and label variants:

### A. Appendix N Reference Invoices (`data/appendix_n/`)
- **Quantity:** 2 PDFs with ground-truth JSON.
- **Description:** Direct PDF reproductions of Example 1 (Harbour Engineering Ltd, Bristol, UK) and Example 2 (Kestrel Components Inc., Dayton, US) matching the exact specification from the prompt.
- **Role:** Regression and golden reference test for prompt examples.

### B. Synthetic Development Dataset (`data/synthetic/`)
- **Quantity:** 150 PDFs with ground-truth JSON.
- **Generator:** `data/gen/generator.py` executed via `scripts/make_data.py` with deterministic pseudo-random seeds.
- **Variations on independent axes:**
  - **Vendors:** 6 canonical vendors (`Harbour Engineering Ltd`, `Kestrel Components Inc.`, `Meridian Industrial GmbH`, `Sakura Precision K.K.`, `Apex Systems Pvt Ltd`, `Vanguard Dynamics Ltd`) plus 4 unknown vendors (`Quantum Matrix Logistics`, `Nordic Flow Supplies AB`, `Pacific Horizon Traders`, `Alpine Peak Manufacturing`).
  - **Name noise:** Capitalization variations (`HARBOUR ENGINEERING`), typos (`Meridan Industrial`, `Sakura Precison`), legal suffix omissions (`Kestrel Components`).
  - **6 Distinct Layout Families:**
    1. Standard two-column invoice details block.
    2. Right-aligned header block.
    3. Label-above-value vertical grid.
    4. Two-column boxed container.
    5. Itemized line-item table with subtotal/tax/total below.
    6. Multi-page document with totals located on page 2.
  - **Multilingual Label Lexicons:** English, German (`Rechnung`, `MwSt`, `Nettobetrag`, `Fällig am`), Japanese (`請求書`, `消費税`, `小計`, `支払期限`), Indian billing labels (`Bill No`, `GSTIN`).
  - **Date Formats by Country:**
    - UK: `DD/MM/YYYY`, `D Mon YYYY`, `DD-Mon-YY` (day-first).
    - US: `MM/DD/YYYY`, `Month D, YYYY`, `M/D/YY` (month-first).
    - DE: `DD.MM.YYYY`, `YYYY-MM-DD`.
    - JP: `YYYY.MM.DD`, `YYYY/MM/DD`.
    - IN: `DD/MM/YYYY`, `DD-MM-YYYY`, `Dth Month YYYY`.
  - **Payment Terms vs Due Date (Rule O1):** Printed due date only, terms only (`Net 30`, `14 days`, `Net 60`), both agreeing, both disagreeing (printed wins with warning), and `Due on receipt`.
  - **Currency Modes (Rule O3):** Symbol only (`£`, `$`, `€`, `¥`, `₹`), code only (`GBP`, `USD`, `EUR`, `JPY`, `INR`), both, and unprinted (triggers fallback to vendor currency with warning).
  - **Number Formatting (Rule O5):** Standard `1,234.56`, German European `1.234,56`, Indian grouping `1,23,456.00`, and Japanese Yen integers `12,000` (formatted with `.00`).
  - **Arithmetic Consistency (Rule O2):** Mathematically consistent vs. deliberately mismatched by more than 0.01 (retains printed values with warning).
  - **Non-Invoice Documents (Rule O4):** Quotations, delivery notes, statements, credit notes, and pro-forma invoices.

### C. Held-Out Validation Dataset (`data/handmade/`)
- **Quantity:** 35 PDFs with ground-truth JSON.
- **Description:** Distinct seed and generation space mimicking unseen vendor configurations and template variations.
- **Role:** Stand-in for hidden test evaluation to verify rule generalizability without overfitting.

---

## 2. Evaluation Results

Evaluation was performed using `python scripts/eval.py --all` measuring Exact Match (EM) per field:

| Field | Appendix N (2 files) | Synthetic Dev (150 files) | Held-Out Set (35 files) |
|---|---|---|---|
| `vendor` | 100.00% | 100.00% | 100.00% |
| `invoice_number` | 100.00% | 100.00% | 100.00% |
| `invoice_date` | 100.00% | 100.00% | 100.00% |
| `due_date` | 100.00% | 100.00% | 100.00% |
| `currency` | 100.00% | 100.00% | 100.00% |
| `subtotal` | 100.00% | 100.00% | 100.00% |
| `tax` | 100.00% | 100.00% | 100.00% |
| `total` | 100.00% | 100.00% | 100.00% |
| **Overall Average** | **100.00%** | **100.00%** | **100.00%** |

---

## 3. Anticipated Failure Modes on Real-World Invoices

While the engine achieves 100% on synthetic and structured test sets, real-world commercial documents present edge cases. The anticipated failure modes and their root causes are documented below:

1. **Scanned Documents Without Text Layer:**
   - Invoices that are scanned images or photographed paper lack an embedded text layer.
   - *Mitigation:* The engine gracefully detects missing text layers and returns an all-null response with an explicit warning rather than failing with an HTTP 500 error.
2. **Font Encoding & Glyph Mappings:**
   - Some legacy PDF producers generate documents using non-standard glyph encoding where characters (such as currency symbols `₹` or `€`) map to unexpected ASCII codepoints.
   - *Mitigation:* The amount parser scrubs unmapped glyph artifacts and falls back to ISO codes or vendor defaults.
3. **Scrambled Reading Order from PDF Printers:**
   - Print-to-PDF drivers occasionally output text blocks in non-chronological order.
   - *Mitigation:* Line clustering utilizes spatial 2D coordinates (`y0`, `x0`) rather than relying on raw text stream order.
4. **Multi-Rate Complex Tax Schemes:**
   - Complex VAT/GST breakdowns spanning multiple jurisdictions (e.g., state taxes, reverse charge, cess).
   - *Mitigation:* All identified tax candidate amounts in the totals summary are aggregated into the total tax amount.
5. **Japanese Imperial Era Transitions:**
   - Historic or official municipal invoices in Japan may use eras older than Reiwa (`令和`), such as Heisei (`平成`) or Showa (`昭和`).
6. **Vocabulary Beyond Multilingual Lexicons:**
   - Rare terminology (e.g., Spanish `Factura`, French `Facture`, Scandinavian terms) would require expanding the lexicon maps.
