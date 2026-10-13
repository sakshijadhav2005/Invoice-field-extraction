# NOTES.md: Architectural Decisions & Business Rules

## 1. Architectural Decisions

- **Pure Python + PyMuPDF + Candidate Scoring:**
  - Evaluated against heavyweight transformer models and OCR engines. PyMuPDF extracts spatial text bounding boxes offline in under 15 ms without cloud APIs or GPUs.
  - Candidate scoring with feature weighting (label proximity, coordinate alignment, arithmetic validation) provides transparency, deterministic debugging, and zero hallucination.
- **FastAPI + Vanilla UI (No React, No Node.js):**
  - Eliminates build pipelines, Node.js dependencies, and network CDN dependencies.
  - The static web page at `/` runs entirely offline with modern vanilla HTML/CSS/JS.
- **Stateless Architecture (No Database):**
  - Keeps the service stateless, portable, and reliable across container and local execution environments.

---

## 2. Ambiguity & Locale Resolution

- **Date Ambiguity by Vendor Country:**
  - When day and month are both $\le 12$ without month names (e.g. `09/03/2026`), vendor country dictates reading order:
    - **US:** Month-first (`MM/DD/YYYY`).
    - **UK, DE, JP, IN:** Day-first (`DD/MM/YYYY`).
  - Dates with either part $> 12$ are inherently unambiguous and parsed directly regardless of country.
  - For unknown vendors, currency hint (`USD` vs others) resolves ambiguity with lower confidence.
  - Ambiguity resolutions always attach a descriptive warning to the response.

---

## 3. Business Rules Implementation (O1–O5)

| Rule | Description | Implementation Strategy |
|---|---|---|
| **O1** | Terms vs. Due Date | If printed due date exists, it is preserved. If terms conflict with printed date, printed date is kept and a warning is logged. If only terms exist (`Net 30`, `14 days`), `due_date = invoice_date + N days` is computed with a warning. `Due on receipt` leaves due date as `null`. |
| **O2** | Arithmetic Cross-Check | If printed `subtotal + tax != total` by $> 0.01$, printed values are preserved and warning `"Subtotal + tax ≠ total."` is issued. Printed numbers are never artificially modified. |
| **O3** | Currency Fallback | If currency symbol/code is absent, falls back to the canonical vendor currency with lowered confidence (0.50) and warning `"Currency not printed, vendor currency used."` |
| **O4** | Document Type Classification | Documents identified as quotations, delivery notes, statements, credit notes, or pro-forma invoices set all extraction fields to `null`, preserve the vendor, and add a warning. |
| **O5** | Locale-Aware Amounts & JPY | All amounts (US, European comma-decimal, Indian lakhs, and JPY integers) are normalized to floats with two decimal places (e.g., `12000.00`). |

---

## 4. Confidence Score Calibration

Confidence scores represent evidence strength rather than uncalibrated probabilities:

| Scenario / Field | Typical Confidence | Rationale |
|---|---|---|
| Exact label match + valid shape + arithmetic agreement | `0.98` | Full multi-feature agreement |
| Standard label match without arithmetic cross-check | `0.92 – 0.95` | Valid pattern and geometry |
| Ambiguous date resolved by country rule | `0.80` | Convention applied, slight ambiguity |
| Due date derived from payment terms | `0.90` | Calculated according to Rule O1 |
| Unprinted currency fallback (Rule O3) | `0.50` | Inferred from vendor metadata |
| Field absent or non-invoice document | `0.00` | No evidence present |

---

## 5. Future Enhancements

1. **Lightweight Candidate Ranker:** Train a scikit-learn logistic regression ranker on extracted spatial feature vectors.
2. **Offline OCR Fallback:** Incorporate an offline Tesseract fallback specifically for scanned PDF pages lacking embedded text layers.
3. **Vendor Layout Cache:** Maintain vendor-specific bounding-box coordinate priors for recurring corporate templates.
