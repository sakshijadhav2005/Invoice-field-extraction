# Plan: Use case 3 — Invoice field extraction (Bruviti Campus Drive 2026)

Repo is graded as a self-contained submission.

---

## 0. Decisions up front (read this first)

### 0.1 How to read the PDF

The brief says the input is a PDF with a text layer and that scanned or handwritten invoices are out of scope. So there is nothing to OCR: the text is already in the file. Use a local PDF text library (PyMuPDF) that returns words with their coordinates. It runs fully offline, installs with `pip`, and is fast enough for the 1-second limit.

### 0.2 Stack you proposed vs. what to use

| Your idea | Use it? | Why |
|---|---|---|
| Python | **Yes** | Best libraries for PDF text, fuzzy matching, and PDF generation |
| FastAPI | **Yes** | Matches the brief's default. Serves the API and the page from one process on port 8000 |
| React JS | **No** | Needs Node and a build step. The brief requires one command from a fresh clone. The page is not scored automatically ("plain HTML is enough"). Use one `index.html` with vanilla JS, served by FastAPI at `/` |
| MongoDB / Postgres (Neon) | **No** | The service is stateless. Neon is a cloud database, so it breaks the network-off rule. A database adds startup risk and no score. Keep upload history in the browser's `localStorage` if you want something nice |

Final stack:

- Python 3.11+, FastAPI, uvicorn, python-multipart
- **PyMuPDF** (`pymupdf`) for text with word coordinates. Fast, wheels for all platforms. Fallback: `pdfminer.six` or `pdfplumber` if PyMuPDF returns nothing.
- **rapidfuzz** for vendor-name matching
- Own regex and rule code for dates, amounts, terms, currency (no `dateutil` guessing; ambiguity must follow the vendor-country rule)
- **reportlab** to generate synthetic invoice PDFs (dev only). Optional second producer for layout variety: WeasyPrint or LibreOffice (dev only, never needed at runtime)
- pytest, pytest-socket (or a simple socket-blocking fixture)
- Optional stretch: scikit-learn logistic regression to rank candidate values. Must train in under 5 minutes and under 1 s per request. Only do it if rules are already solid.
- Pin versions in `requirements.txt`. No virtualenv in the repo. No files over 50 MB.

### 0.3 Where the score comes from

Metric: exact match per field on hidden invoices, with layouts, labels and date formats you have not seen. A wrong date scores the same as a missing one. Judges also weigh DATA.md, NOTES.md and tests as much as the metric.

Highest-risk fields, in order: dates (ambiguity, formats, terms), total (which of many amounts), tax (several tax lines, rate vs amount), vendor (misspelt names), then invoice number. Spend time in that order.

Design rule for everything: **generalise, don't memorise**. The hidden set uses unseen layouts. Never key logic to the two Appendix N invoices.

---

## 1. Architecture

```
POST /extract (multipart "file")
  → read bytes, validate PDF, size cap
  → pdf_text.py     words + bboxes → lines → "label: value" pairs, reading-order text
  → doctype.py      invoice | quotation | delivery note | statement | credit note | unknown   (rule O4)
  → vendor.py       canonical vendor or "unknown", + country
  → currency.py     symbol/code → ISO, fallback to vendor currency (rule O3)
  → amounts.py      locale-aware number parsing (1,234.56 / 1.234,56 / 1,23,456.00 / 12,000 JPY)
  → dates.py        all formats, country-based day/month order, ambiguity flag
  → terms.py        Net N / N days / due in N days → due_date (rule O1)
  → fields.py       candidate generation + scoring for invoice_no, subtotal, tax, total, dates
  → checks.py       arithmetic check (O2), date sanity, warnings
  → confidence.py   per-field 0..1
  → JSON response (exact schema from the brief)
GET /health → {"status":"ok"} once models/lexicons are loaded
GET /       → static/index.html (upload form + pretty JSON)
```

Repo layout:

```
.
├── README.md  DATA.md  NOTES.md  AI.md  plan.md
├── requirements.txt
├── run.sh  (and run.bat)         # one command: install deps + start on :8000
├── Dockerfile                     # optional convenience
├── app/
│   ├── main.py                    # FastAPI app, routes, static page
│   ├── schema.py                  # Pydantic response model
│   ├── pdf_text.py  doctype.py  vendor.py  currency.py
│   ├── amounts.py  dates.py  terms.py  fields.py
│   ├── checks.py  confidence.py
│   └── lexicon/                   # label vocabularies (JSON/py): en, de, ja, in
├── static/index.html
├── data/
│   ├── gen/                       # generator code (templates, vocab, noise)
│   ├── synthetic/                 # generated PDFs + .json ground truth (small; or gitignored + regenerated)
│   ├── handmade/                  # PDFs made differently from the generator, used as held-out
│   └── appendix_n/                # the two brief examples as PDFs
├── scripts/
│   ├── make_data.py  eval.py  smoke.py
└── tests/
    ├── test_dates.py  test_amounts.py  test_terms.py  test_currency.py  test_vendor.py
    ├── test_golden_appendix_n.py  test_api_contract.py  test_offline.py  test_perf.py
    └── test_generated_regression.py
```

---

## 2. Phase details

### Phase 1 — Setup and safety net

1. Create a **private** GitHub repo. Add `bruviti-campus` as collaborator immediately (Settings → Collaborators → Add people). Without this the work counts as not submitted.
2. `.gitignore`: `venv/`, `.venv/`, `__pycache__/`, `*.pyc`, `.env`, large generated data.
3. Skeleton FastAPI app:
   - `GET /health` returns 200 `{"status":"ok"}`
   - `POST /extract` returns the full schema with nulls, `vendor:"unknown"`, `currency` guess, empty warnings
   - `GET /` serves a placeholder page
4. `run.sh`: create venv if missing, `pip install -r requirements.txt`, `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
5. Prove it on a clean folder right now (clone to a temp dir, run). Catching a start problem early is much cheaper.
6. Commit, push, then **submit the repo link in the form** (select Use case 3). You will resubmit later.

### Phase 2 — Data gathering and generation

The brief supplies no training data. Finding and building it is graded. Plan three sources:

**A. The two Appendix N invoices as PDFs** (golden tests). Reproduce them as closely as you can with reportlab. Expected output is the brief's Example 1 and 2 JSON.

**B. Synthetic generator (`data/gen/`)** with ground truth JSON per PDF. Vary on independent axes so combinations the grader uses show up:

- Vendor: 6 canonical vendors plus 4–6 fake unknown vendors (for `unknown`)
- Name noise: UPPER CASE, with/without Ltd / Inc / GmbH / KK / Pvt Ltd, `Harbor` vs `Harbour`, `Kestrel Components Inc.`, one or two typos (`Meridan Industrial`, `Sakura Precison`)
- Layout families (at least 6, each with sub-variants): header block with right-aligned key/value pairs; label above value; label and value in a table; two-column "invoice details" box; totals box bottom-right; footer-only totals; multi-page with totals on page 2; line-item table with its own "Total" column that must not be mistaken for the invoice total
- Labels: `Invoice No / Invoice # / Reference # / Inv. No. / Rechnungsnr. / 請求書番号 / Bill No.`; `Invoice Date / Dated / Date of issue / Rechnungsdatum / 請求日`; `Due Date / Payment due / Pay by / Fällig am / 支払期限`; `Subtotal / Sub total / Net amount / Taxable value / Nettobetrag / 小計`; `VAT / GST / Sales tax / MwSt / USt / 消費税`; `Total / Amount Due / Balance Due / Grand Total / Gesamtbetrag / ご請求金額`
- Date formats by country: UK `03/09/2026`, `3 Sep 2026`, `03-Sep-26`; US `9/3/26`, `September 3, 2026`, `09/03/2026`; DE `03.09.2026`, `2026-09-03`; JP `2026.09.03`, `2026/09/03`, `2026年9月3日`; IN `03/09/2026`, `03-09-2026`, `3rd Sep 2026`
- Terms vs due date: due date only; terms only (`Net 30`, `30 days`, `Due in 14 days`); both consistent; both **disagreeing** (rule O1); neither; `Due on receipt`; `2/10 Net 30`
- Currency: symbol, code, both, and **none** (rule O3); `¥` for JPY; `Rs.` and `₹` for INR
- Number formats: `1,234.56`; `1.234,56` (DE); `1,23,456.00` (IN lakh grouping); JPY with no decimals (`12,000`)
- Tax: single line; multiple lines (CGST + SGST, or VAT 20% + levy); tax-exempt (0); rate and amount on the same line (`VAT 20% 72.32`: the rate must not be read as the amount); tax rate written as `7.25%`
- Arithmetic: correct; **mismatching** by more than 0.01 (rule O2, must keep printed values)
- Non-invoices: quotation, delivery note, statement, credit note, pro-forma (rule O4)
- PDF noise: odd text order, extra whitespace, non-breaking spaces, `Rs.`/`₹` glyphs, ligatures, small and large fonts, a watermark word like `COPY` or `PAID`
- Fonts: reportlab built-ins cover Latin-1 and `€`. Use the built-in CID font `HeiseiMin-W3` for Japanese. Bundle `DejaVuSans.ttf` (small) for `₹`.

**C. Hand-made "held-out" set (`data/handmade/`, 30–50 PDFs).** Make these in a different way from the generator: Word or LibreOffice templates exported to PDF, and Google Docs or online invoice-template tools exported to PDF. Vary label wording by hand and by asking an AI assistant to brainstorm vendor-style invoice wordings (allowed for development; list it in AI.md). **Never tune on this set until step 7.** It is your stand-in for the hidden test.

Split rule: generator templates are divided into `dev` templates and `holdout` templates. The holdout templates and label variants are never used while building rules. This mimics "layouts, labels and date formats you have not seen".

Label vocabulary: a few real public invoice samples (company sample invoices, template galleries, open-source invoice generators) can help you write the label lists. Record each source and licence in DATA.md. Do not commit anything you may not redistribute; commit only your own generated files.

Deliverable of this phase: `python scripts/make_data.py` regenerates everything deterministically (fixed seed), and `scripts/eval.py` prints per-field exact-match accuracy plus a confusion list.

### Phase 3 — Normalisers, test-first

Write tests before code. Each normaliser is a pure function.

**dates.py**
- Parse: `dd/mm/yyyy`, `mm/dd/yy`, `yyyy-mm-dd`, `yyyy.mm.dd`, `yyyy/mm/dd`, `dd.mm.yyyy`, `3 Sep 2026`, `Sep 3, 2026`, `3rd September 2026`, `03-Sep-26`, `2026年9月3日`
- Two-digit years: 26 → 2026
- Ambiguous means both parts are 12 or less and the format has no month name. Resolve by vendor country: day-first for UK, DE, JP, IN; month-first for US. If either part is greater than 12, it is not ambiguous, whatever the country. Add a warning when ambiguity was resolved by country.
- Unknown vendor: use currency as the country hint (USD → month-first, everything else day-first), lower confidence, add a warning.
- Cross-check: due date should not be before invoice date. If it is, consider the alternative reading and warn.
- Reject impossible dates (`31/02/2026`).
- Stretch: Japanese era years (`令和8年9月3日`).

**terms.py** (rule O1)
- `Net 30`, `Net30`, `N30`, `30 days`, `Payment within 30 days`, `due in 30 days`, `Terms: 30` → days
- `2/10 Net 30` → use 30
- If both a printed due date and terms exist and disagree: **use the printed date and add a warning**
- `Due on receipt` / `Immediate`: decide and document (default: `due_date = null` plus a warning, since the brief does not say)
- Output `due_date = invoice_date + N days`; add a warning "Due date derived from terms Net 30." as in Example 2

**amounts.py**
- Detect the locale from the string itself: if the last separator has exactly 2 digits after it, it is the decimal mark (`1.234,56` → 1234.56). If a `,` has 3 digits after it and no other separator follows, it is a thousand separator (`12,000`). Indian grouping `1,23,456.00`. Spaces and apostrophes as separators.
- Strip currency symbols, codes, `Rs.`, trailing `-`, parentheses negatives
- Output with two decimals, no thousands separators. JPY: `.00` (rule O5)
- Do not mistake `20%` or `7.25%` for an amount

**currency.py**
- Symbol and code table: `£ GBP`, `$ USD`, `€ EUR`, `¥ JPY / 円`, `₹ Rs. INR`
- `¥` resolves to JPY (it is the only yen/yuan currency in scope)
- Fallback to the vendor's Appendix M currency (rule O3) with lowered confidence and a warning
- If the printed currency conflicts with the vendor's, trust the print and add a warning

### Phase 4 — PDF text, vendor, doctype

**pdf_text.py**
- Extract words with coordinates, rebuild lines by clustering on y with a tolerance, keep both a reading-order text and a layout-aware grid.
- Build `(label, value)` candidates in three geometries: same line (`label: value`), value to the right in another column, value on the line directly below the label.
- Handle all pages. Guard: if there is no text layer, return all-null with a warning "no text layer (scanned?)" and a 200 response (never a 500).
- Cache the parsed page structure for the request. Keep total time well under 1 s.

**vendor.py**
- Normalise names: lowercase, strip punctuation, strip legal suffixes (`ltd, limited, inc, incorporated, llc, gmbh, kk, k.k., 株式会社, pvt, private`), British/American spelling folding (`harbor`→`harbour`), remove double spaces.
- Match with rapidfuzz (`token_set_ratio` plus `partial_ratio`) against canonical names and an alias list. Scan the top of page 1 first, then the footer, then the whole text.
- Extra evidence beyond the name: city and country words (Bristol, Dayton, Germany, Japan, India), tax-id formats (UK `VAT No GB…`, India `GSTIN`, Germany `USt-IdNr / DE…`, Japan `T` plus 13 digits), currency, email domain.
- Threshold: below it → `"unknown"` with low confidence and the warning "Vendor name not in the canonical list."
- Guard against `Bill to: Bruviti Services Pvt Ltd` and `Sold to`: the customer name is Bruviti, which is not a vendor. Never return it.

**doctype.py** (rule O4)
- Title and keyword scoring: `invoice`, `tax invoice`, `Rechnung`, `請求書` versus `quotation / quote / estimate`, `delivery note / packing slip`, `statement of account`, `credit note`, `pro forma`.
- Non-invoice: every field null, vendor as found, warning naming the document type. Decide how to show "vendor as found" for an unmatched name (default: the canonical name if it matches, otherwise the raw header name). Document the choice.

### Phase 5 — Field extractors

Candidate-and-score approach, not first-regex-wins. For each field generate candidates and score them on features, then pick the best and derive confidence from the margin.

**invoice_number**: label lexicon match plus a value shape (letters/digits/dashes, 3+ chars, not a date, not a phone number, not a VAT or GST id). Prefer the label closest to the top of page 1. Return as printed, trimmed. Skip `Page 1 of 2`, `PO Number`, `Customer No`.

**invoice_date**: label lexicon match (`Invoice Date`, `Dated`, `Date`, `Issued`). A bare `Date` label is weaker than `Invoice Date`. Ignore `Due`, `Ship`, `Order`, `Delivery` dates.

**due_date**: explicit label, else terms (rule O1). Warnings as described above.

**subtotal / tax / total** (the bulk of the points):
- Find the totals block: lines near the bottom of the last page, right-aligned numbers, a sequence like subtotal → tax → total.
- `subtotal`: `Subtotal`, `Sub total`, `Net`, `Taxable value`, `Amount before tax`.
- `tax`: sum **all** tax lines (VAT, GST, CGST + SGST, IGST, 消費税). Never take the percentage as the value (`VAT 20% 72.32` → 72.32).
- `total`: `Amount Due`, `Balance Due`, `Total Due`, `Grand Total`, `Total` (weakest). Prefer the lowest/last of the totals. Ignore the line-item `Total` column header and per-line amounts. Ignore "amount in words".
- Cross-check: choose the candidate triple for which `subtotal + tax = total` within 0.01 when one exists. If none fits, return the printed values and add a warning. **Never "fix" the arithmetic** (rule O2).
- If a field is truly not printed, return null rather than inventing it. Document this and the one exception you consider (e.g. only when the layout clearly prints two of three).

**Evaluation after every change:** run `scripts/eval.py` on dev and on holdout and look at the worst field first.

Milestone: end-to-end baseline. Commit, push, resubmit the form.

### Phase 6 — Warnings, confidence, UI

**Warnings** (strings, human-readable, as in the brief's examples):
- Date resolved by country order (`Date 9/3/26 read as month-first (US vendor).`)
- Due date derived from terms
- Printed due date and terms disagree
- Subtotal + tax ≠ total
- Currency not printed, vendor currency used
- Vendor not in the canonical list
- No due date or payment terms found
- Document is a quotation / delivery note / statement
- No text layer found

**Confidence**: a number 0–1 per field, from the candidate's score margin and the evidence type. Rough guide: label match exact + shape valid + arithmetic agrees → 0.9+; ambiguous date resolved by country → around 0.8 (Example 2 shows 0.8); field absent → 0.0 (Example 3); fallback currency → around 0.5. Use the synthetic validation set to check that high-confidence fields are right more often than low-confidence ones (a small reliability table goes in NOTES.md).

**UI (`static/index.html`)**: file picker, an Extract button, a pretty-printed JSON panel, a table of fields with a coloured confidence bar, and the warnings list. Vanilla JS using `fetch('/extract')` with `FormData` (field name `file`). No CDN, no build step, works offline.

**API hardening**: non-PDF upload → 400 with a clear message; empty file → 400; oversize → 413; encrypted or corrupt PDF → 200 all-null plus a warning rather than a crash. Never return a 500 on bad input. Response always matches the schema.

### Phase 7 — Held-out stress test and error analysis

Testing and error analysis steps:
1. Run on `handmade/` and `holdout` templates. Record per-field accuracy. This is your honest estimate of the hidden score.
2. Group failures by cause (label not in lexicon, wrong amount picked, locale parse, date ambiguity, vendor miss, doctype miss). Fix the causes that cost the most points first, with a general fix, not a special case.
3. Add every fixed failure as a regression test.
4. Adversarial pass: write 10 weird invoices on purpose (label under value, totals at top of the page, two currencies mentioned, vendor name only in the footer, tax line with a rate and amount in separate columns, German `1.234,56 €`, Japanese `¥12,000` with `消費税 (10%) 1,200`, Indian `₹1,18,000.00`). Fix what breaks.
5. Time test: 50 invoices, check the slowest request is under 1 s (aim under 300 ms) including the first request after startup.
6. Optional stretch, only if everything above is green: small logistic-regression candidate ranker trained on the generator data in under 5 minutes, compared against the rules on holdout. Keep it only if it wins on holdout; otherwise note it in NOTES.md as "tried, not kept".

### Phase 8 — Documentation

Write all four files from the actual results, not from the plan.

- **README.md**: the one command to install and start (`./run.sh`, with the Windows equivalent), the health URL, how to open the page at `/`, how to run tests (`pytest`), how to regenerate data and run `scripts/eval.py`. Assume the reader has never seen the repo. Include the Python version.
- **DATA.md**: where each data source came from (generator, handmade, any public samples with licences), how each was made, how you split dev from holdout, how you used it to test, the per-field results, and what you expect to break on real data (scanned invoices, unusual fonts, text order scrambled by the PDF producer, totals split over pages, rare tax schemes, Japanese eras, label wordings outside the lexicon). Be honest about the gap between synthetic and real.
- **NOTES.md** (one page at most): decisions (why rules plus candidate scoring, why not a database or React), ambiguity handling by vendor country, what was cut and why, what you would do next (a trained ranker, a layout classifier per vendor, more real samples, an OCR path for scans).
- **AI.md**: every AI tool used and what for (for example: brainstorming label vocabularies and layout variants, drafting generator code, test ideas). You will be asked to explain your own code, so only keep code you understand.

### Phase 9 — Release hardening

Do this on a clean machine or a fresh clone in a temp folder, not in your working folder.

Checklist:
- [ ] `git clone` into a new directory, run only the README command, wait for `/health`, then call `/extract` with the Appendix N PDFs
- [ ] Switch the network off (or run with sockets blocked) and repeat; the service must still start and answer
- [ ] Port is 8000, host `0.0.0.0`; `GET /health` returns `{"status":"ok"}` only when ready
- [ ] `GET /` shows the page and the upload works
- [ ] `pytest` passes without network
- [ ] No venv, secrets, `.env`, or files over 50 MB are committed
- [ ] `requirements.txt` is pinned and installs on a clean Python 3.11 (also try 3.12)
- [ ] Response matches the schema exactly: eight fields, `confidence` has eight keys, `warnings` is an array, amounts are numbers with no thousands separators
- [ ] README, DATA.md, NOTES.md (one page), AI.md all present
- [ ] `bruviti-campus` is a collaborator and the repo is private
- [ ] Final `git push`, check on github.com that the latest commit is visible

### Phase 10 — Final submission

Resubmit the repo link in the form (select Use case 3) even if the link has not changed. Verify repository and submission integrity.

---

## 3. Test plan

| Layer | What | Where |
|---|---|---|
| Unit | Dates (formats, ambiguity per country, invalid), amounts (all locales, JPY), terms, currency, vendor normalisation and fuzzy match | `tests/test_*.py` |
| Golden | Appendix N invoices as PDFs give exactly Example 1 and Example 2 fields (confidence values only need to be in range) | `test_golden_appendix_n.py` |
| Business rules | One test per rule O1–O5, including the "do not correct arithmetic" case | `test_rules.py` |
| Contract | `/health`, `/extract` schema, bad inputs (non-PDF, empty, corrupt), content type, field name `file` | `test_api_contract.py` |
| Regression | Generated dev set must stay above a threshold per field; failures found later are added as fixed cases | `test_generated_regression.py` |
| Held-out | `scripts/eval.py --holdout` reports the honest score (not a pass/fail test, a report) | `scripts/eval.py` |
| Offline | Sockets blocked for the whole test session; service must start and answer | `test_offline.py` |
| Performance | p95 request under 1 s on the 50-file set | `test_perf.py` |

---

## 4. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Service does not start on the grader's machine → score zero | Clean-clone test in Phase 1 and again in Phase 9; pinned deps; one command; no system packages at runtime |
| Overfitting to own generator | Holdout templates, handmade PDFs made a different way, adversarial set |
| Day/month mix-ups | Country rule with unit tests for every vendor; unambiguous values (day > 12) always win; warnings added |
| Wrong total picked | Candidate scoring plus arithmetic cross-check; ignore line-item columns and amounts in words |
| Tax rate read as amount | Explicit tests (`VAT 20% 72.32`, `7.25% 16.37`) |
| Misspelt vendor names | Normalisation + fuzzy match + secondary evidence (city, tax-id, currency); `unknown` below threshold |
| Text order scrambled by a PDF producer | Use word coordinates, not raw text order; test with PDFs from two producers |
| Slow requests | Parse once per request, no heavy models, measure p95 |
| Time sink on stretch goals | Stretch only after Phase 7 is green; cut and record in NOTES.md |
| Submission integrity | Early and repeated submissions; freeze code early with protected buffer |

---

## 5. Open decisions to settle early (write the choice in NOTES.md)

1. `Due on receipt`: null plus warning, or due date equal to invoice date? (Default: null plus warning.)
2. Subtotal not printed: null, or derive as total minus tax? (Default: null, because the hidden labels probably follow what is printed.)
3. Non-invoice documents: for an unmatched vendor, return the raw name found in the header. Matched vendors return the canonical name.
4. Unknown vendor and ambiguous date: use currency as the country hint and lower the date confidence.
5. Multiple tax lines: report the sum as `tax` (the brief says "Total tax on the invoice").

---

## 6. Development Workflow

- Commit at the end of every phase with a clear message. Push every time.
- Run `pytest` and `scripts/eval.py` before every commit and paste the scores into the commit message.
- Keep a running list of "things that broke" as you go. It becomes the "what you expect to break" section of DATA.md for free.
- If a phase runs over, prioritize core requirements and adjust scope.
