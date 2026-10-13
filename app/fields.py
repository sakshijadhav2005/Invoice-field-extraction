import re
from typing import Dict, List, Optional, Tuple
from app.schema import ExtractionResponse, ConfidenceScores
from app.pdf_text import DocumentInfo, LineBox, WordBox
from app.vendor import match_vendor
from app.doctype import classify_document
from app.currency import resolve_currency
from app.dates import parse_date
from app.terms import resolve_due_date, extract_terms_days
from app.amounts import parse_amount

INVOICE_NO_LABELS = [
    r'invoice\s*(?:no|number|#|id|num)',
    r'inv\s*(?:no|number|#|\.)',
    r'reference\s*(?:no|number|#)',
    r'ref\s*(?:no|number|#)',
    r'rechnungs(?:nr|nummer)',
    r'請求書番号',
    r'請求番号',
    r'bill\s*(?:no|number|#)',
]

INVOICE_DATE_LABELS = [
    r'invoice\s*date',
    r'date\s*of\s*issue',
    r'issue\s*date',
    r'rechnungsdatum',
    r'請求日',
    r'bill\s*date',
    r'dated',
]

DUE_DATE_LABELS = [
    r'due\s*date',
    r'payment\s*due',
    r'pay\s*by',
    r'fällig\s*(?:am)?',
    r'fälligkeitsdatum',
    r'支払期限',
    r'期日',
]

SUBTOTAL_LABELS = [
    r'subtotal',
    r'sub\s*total',
    r'sub-total',
    r'net\s*amount',
    r'taxable\s*value',
    r'nettobetrag',
    r'netto',
    r'小計',
    r'amount\s*before\s*tax',
]

TAX_LABELS = [
    r'vat',
    r'tax',
    r'sales\s*tax',
    r'gst',
    r'cgst',
    r'sgst',
    r'igst',
    r'mwst',
    r'ust',
    r'消費税',
]

TOTAL_LABELS = [
    r'amount\s*due',
    r'balance\s*due',
    r'total\s*due',
    r'grand\s*total',
    r'gesamtbetrag',
    r'ご請求金額',
    r'invoice\s*total',
    r'total\s*amount',
    r'total',
]

def _extract_segments_from_line(line: LineBox) -> List[Tuple[str, float, float]]:
    """
    Splits a line into horizontal column segments when words have a noticeable horizontal gap (> 15 pt).
    Returns list of (segment_text, x0, x1).
    """
    if not line.words:
        text = line.text.strip()
        return [(text, line.x0, line.x1)] if text else []

    segments: List[Tuple[str, float, float]] = []
    current_words: List[WordBox] = [line.words[0]]

    for w in line.words[1:]:
        prev_w = current_words[-1]
        gap = w.x0 - prev_w.x1
        if gap > 15.0:
            seg_text = " ".join(x.text for x in current_words).strip()
            if seg_text:
                segments.append((seg_text, current_words[0].x0, prev_w.x1))
            current_words = [w]
        else:
            current_words.append(w)

    if current_words:
        seg_text = " ".join(x.text for x in current_words).strip()
        if seg_text:
            segments.append((seg_text, current_words[0].x0, current_words[-1].x1))

    return segments

def _extract_all_pairs(lines: List[LineBox]) -> List[Tuple[str, str, float]]:
    """
    Extracts candidate (label, value_text, score) tuples using:
    1. Same segment ("Label: Value" or "Label - Value")
    2. Column-aligned vertical pairs (Label at line i, Value at line i+1 directly underneath)
    3. Next line if line i is a pure label
    """
    pairs: List[Tuple[str, str, float]] = []

    # 1. Segment-level pairs
    for i, line in enumerate(lines):
        segments = _extract_segments_from_line(line)
        for seg_text, sx0, sx1 in segments:
            if ':' in seg_text:
                parts = seg_text.split(':', 1)
                lbl, val = parts[0].strip(), parts[1].strip()
                if lbl and val:
                    pairs.append((lbl, val, 1.0))
            elif ' - ' in seg_text:
                parts = seg_text.split(' - ', 1)
                lbl, val = parts[0].strip(), parts[1].strip()
                if lbl and val:
                    pairs.append((lbl, val, 0.85))

        # 2. Next-line pair if current line is a short label
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            if len(line.text.split()) <= 4 and not re.search(r'\d{3,}', line.text) and line.text.count(':') <= 1:
                pairs.append((line.text.strip(), next_line.text.strip(), 0.75))

    # 3. Column-aligned vertical pairs (e.g. Layout 2: label row above value row)
    for i in range(len(lines) - 1):
        top_line = lines[i]
        bottom_line = lines[i + 1]
        v_dist = bottom_line.y0 - top_line.y0
        if 5.0 <= v_dist <= 30.0:
            top_segs = _extract_segments_from_line(top_line)
            bottom_segs = _extract_segments_from_line(bottom_line)
            for t_text, tx0, tx1 in top_segs:
                # If top segment has text after colon, it's a self-contained pair on the same line
                colon_val = t_text.split(':', 1)[1].strip() if ':' in t_text else ""
                if colon_val:
                    continue
                for b_text, bx0, bx1 in bottom_segs:
                    if abs(tx0 - bx0) <= 25.0 and len(t_text.split()) <= 4:
                        pairs.append((t_text, b_text, 0.90))

    return pairs

def extract_invoice_fields(doc_info: DocumentInfo) -> ExtractionResponse:
    """
    End-to-end invoice field extraction:
    - Text layer validation
    - Document classification (Rule O4)
    - Vendor normalization & matching
    - Currency resolution (Rule O3)
    - Invoice number, dates, terms (Rule O1)
    - Amounts & arithmetic validation (Rule O2 & O5)
    - Confidence scoring & human-readable warnings
    """
    # 1. Guard against scanned / empty PDFs
    if not doc_info.has_text_layer or not doc_info.full_text.strip():
        return ExtractionResponse(
            vendor="unknown",
            confidence=ConfidenceScores(
                invoice_number=0.0, invoice_date=0.0, due_date=0.0,
                subtotal=0.0, tax=0.0, total=0.0, currency=0.0, vendor=0.0
            ),
            warnings=["No text layer found (scanned document or empty)."]
        )

    all_warnings: List[str] = []

    # 2. Match vendor
    vendor_res = match_vendor(doc_info.full_text)
    vendor_name = vendor_res.canonical_name
    vendor_country = vendor_res.country
    vendor_curr = vendor_res.default_currency
    all_warnings.extend(vendor_res.warnings)

    # 3. Classify document type (Rule O4)
    doctype_res = classify_document(doc_info.full_text)
    if not doctype_res.is_invoice:
        all_warnings.extend(doctype_res.warnings)
        return ExtractionResponse(
            invoice_number=None,
            invoice_date=None,
            due_date=None,
            subtotal=None,
            tax=None,
            total=None,
            currency=None,
            vendor=vendor_name,
            confidence=ConfidenceScores(
                invoice_number=0.0, invoice_date=0.0, due_date=0.0,
                subtotal=0.0, tax=0.0, total=0.0, currency=0.0,
                vendor=vendor_res.confidence
            ),
            warnings=all_warnings
        )

    # 4. Resolve currency (Rule O3)
    curr_res = resolve_currency(doc_info.full_text, vendor_currency=vendor_curr)
    all_warnings.extend(curr_res.warnings)

    # Collect all lines across pages
    all_lines: List[LineBox] = []
    for page in doc_info.pages:
        all_lines.extend(page.lines)

    kv_pairs = _extract_all_pairs(all_lines)

    # -------------------------------------------------------------------------
    # 5. Extract Invoice Number
    # -------------------------------------------------------------------------
    inv_num_val: Optional[str] = None
    inv_num_conf = 0.0

    RESERVED_WORDS = {
        'invoice', 'date', 'dated', 'rechnungsdatum', 'due', 'total',
        'subtotal', 'tax', 'bill', 'reference', 'page', 'order',
        'customer', 'terms', 'payment'
    }

    # 5a. Check candidate pairs
    for lbl, val, score in kv_pairs:
        lbl_lower = lbl.lower()
        if any(re.search(pat, lbl_lower) for pat in INVOICE_NO_LABELS):
            clean_val = re.sub(r'^[#:\-\s]+', '', val).split()[0] if val.strip() else ""
            if clean_val.lower() in RESERVED_WORDS:
                continue
            if re.match(r'^[A-Za-z0-9\-_/]{3,35}$', clean_val):
                # Reject pure dates
                if not re.match(r'^\d{4}[-/.]\d{2}[-/.]\d{2}$', clean_val) and not re.match(r'^\d{2}[-/.]\d{2}[-/.]\d{4}$', clean_val):
                    inv_num_val = clean_val
                    inv_num_conf = 0.95 * score
                    break

    # 5b. Direct regex scanning on lines (handles multiple items on one line)
    if not inv_num_val:
        for line in all_lines[:25]:
            m = re.search(
                r'(?:invoice|inv|rechnungs(?:nr|nummer)?|bill|reference|ref)(?:\s*(?:no|number|#|nr|\.))[:\s#]*([A-Za-z0-9\-_/]{3,35})\b',
                line.text,
                re.IGNORECASE
            )
            if not m:
                m = re.search(r'(?:請求書番号|請求番号)[:\s#]*([A-Za-z0-9\-_/]{3,35})\b', line.text)

            if m:
                cand = m.group(1).strip()
                if cand.lower() in RESERVED_WORDS:
                    continue
                if not re.match(r'^\d{4}[-/.]\d{2}[-/.]\d{2}$', cand) and not re.match(r'^\d{2}[-/.]\d{2}[-/.]\d{4}$', cand):
                    inv_num_val = cand
                    inv_num_conf = 0.92
                    break

    # -------------------------------------------------------------------------
    # 6. Extract Invoice Date
    # -------------------------------------------------------------------------
    inv_date_val: Optional[str] = None
    inv_date_conf = 0.0

    # 6a. Check pairs with explicit invoice date label
    best_inv_date: Optional[str] = None
    best_inv_score = 0.0
    for lbl, val, score in kv_pairs:
        lbl_lower = lbl.lower()
        if any(re.search(pat, lbl_lower) for pat in INVOICE_DATE_LABELS):
            d_res = parse_date(val, country=vendor_country, currency_hint=curr_res.currency)
            if d_res and d_res.iso_date:
                cand_score = d_res.confidence * score
                if cand_score > best_inv_score:
                    best_inv_score = cand_score
                    best_inv_date = d_res.iso_date
                    all_warnings.extend(d_res.warnings)

    inv_date_val = best_inv_date

    # 6b. Direct regex scanning for explicit date labels
    if not inv_date_val:
        for line in all_lines[:25]:
            m = re.search(
                r'(?:invoice\s*date|date\s*of\s*issue|issue\s*date|rechnungsdatum|dated|bill\s*date|請求日)[:\s]*([^\s,;]+(?:\s+[^\s,;]+){0,3})',
                line.text,
                re.IGNORECASE
            )
            if m:
                d_res = parse_date(m.group(1).strip(), country=vendor_country, currency_hint=curr_res.currency)
                if d_res and d_res.iso_date:
                    inv_date_val = d_res.iso_date
                    inv_date_conf = d_res.confidence * 0.90
                    all_warnings.extend(d_res.warnings)
                    break

    # 6c. Fallback to generic Date label
    if not inv_date_val:
        for lbl, val, score in kv_pairs:
            lbl_lower = lbl.lower()
            if 'date' in lbl_lower and not any(w in lbl_lower for w in ['due', 'ship', 'delivery', 'pay']):
                d_res = parse_date(val, country=vendor_country, currency_hint=curr_res.currency)
                if d_res and d_res.iso_date:
                    inv_date_val = d_res.iso_date
                    inv_date_conf = d_res.confidence * 0.85
                    all_warnings.extend(d_res.warnings)
                    break

    # -------------------------------------------------------------------------
    # 7. Extract Due Date and Terms (Rule O1)
    # -------------------------------------------------------------------------
    printed_due_date_iso: Optional[str] = None
    terms_text: Optional[str] = None
    best_due_score = 0.0

    for lbl, val, score in kv_pairs:
        lbl_lower = lbl.lower()
        if any(re.search(pat, lbl_lower) for pat in DUE_DATE_LABELS):
            d_res = parse_date(val, country=vendor_country, currency_hint=curr_res.currency)
            if d_res and d_res.iso_date:
                cand_score = d_res.confidence * score
                if cand_score > best_due_score:
                    best_due_score = cand_score
                    printed_due_date_iso = d_res.iso_date
                    all_warnings.extend(d_res.warnings)

    if not printed_due_date_iso:
        for line in all_lines[:30]:
            m = re.search(
                r'(?:due\s*date|payment\s*due|pay\s*by|fällig\s*(?:am)?|fälligkeitsdatum|支払期限)[:\s]*([^\s,;]+(?:\s+[^\s,;]+){0,3})',
                line.text,
                re.IGNORECASE
            )
            if m:
                d_res = parse_date(m.group(1).strip(), country=vendor_country, currency_hint=curr_res.currency)
                if d_res and d_res.iso_date:
                    printed_due_date_iso = d_res.iso_date
                    all_warnings.extend(d_res.warnings)
                    break

    # Scan for payment terms text
    for line in all_lines:
        line_txt = line.text
        if re.search(r'\b(?:Net\s*\d+|N\d+|\d+\s*days|due\s+in\s+\d+|due\s+on\s+receipt|immediate)\b', line_txt, re.IGNORECASE):
            terms_text = line_txt
            break

    due_res = resolve_due_date(
        invoice_date_iso=inv_date_val,
        printed_due_date_iso=printed_due_date_iso,
        terms_text=terms_text
    )
    due_date_val = due_res.due_date_iso
    due_date_conf = due_res.confidence
    all_warnings.extend(due_res.warnings)

    # -------------------------------------------------------------------------
    # 8. Extract Amounts: Subtotal, Tax, Total
    # -------------------------------------------------------------------------
    subtotal_candidates: List[float] = []
    tax_candidates: List[float] = []
    total_candidates: List[float] = []

    for line in all_lines:
        txt = line.text.strip()
        txt_lower = txt.lower()

        # Check for Total
        if any(re.search(rf'\b{pat}\b', txt_lower) for pat in TOTAL_LABELS):
            if not any(re.search(rf'\b{spat}\b', txt_lower) for spat in SUBTOTAL_LABELS):
                parts = txt.split()
                for p in reversed(parts):
                    amt = parse_amount(p)
                    if amt is not None and amt > 0:
                        total_candidates.append(amt)
                        break

        # Check for Subtotal
        if any(re.search(rf'\b{pat}\b', txt_lower) for pat in SUBTOTAL_LABELS):
            parts = txt.split()
            for p in reversed(parts):
                amt = parse_amount(p)
                if amt is not None and amt > 0:
                    subtotal_candidates.append(amt)
                    break

        # Check for Tax lines
        if any(re.search(rf'\b{pat}\b', txt_lower) for pat in TAX_LABELS):
            # Exclude company tax registration IDs (VAT No, USt-IdNr, GSTIN, Tax ID, etc.)
            if re.search(r'\b(?:vat\s*(?:no|reg|number|#)|ust[-]?idnr|gstin|tax\s*id|ein|tin)\b', txt_lower):
                continue

            if not any(re.search(rf'\b{spat}\b', txt_lower) for spat in SUBTOTAL_LABELS + TOTAL_LABELS):
                parts = txt.split()
                for p in reversed(parts):
                    amt = parse_amount(p)
                    if amt is not None and amt >= 0:
                        tax_candidates.append(amt)
                        break

    # If multiple tax lines found, sum them up
    tax_val: Optional[float] = sum(tax_candidates) if tax_candidates else None
    subtotal_val: Optional[float] = subtotal_candidates[-1] if subtotal_candidates else None
    total_val: Optional[float] = total_candidates[-1] if total_candidates else None

    # Cross-check arithmetic (Rule O2)
    subtotal_conf = 0.95 if subtotal_val is not None else 0.0
    tax_conf = 0.95 if tax_val is not None else 0.0
    total_conf = 0.95 if total_val is not None else 0.0

    if subtotal_val is not None and tax_val is not None and total_val is not None:
        expected_total = round(subtotal_val + tax_val, 2)
        if abs(expected_total - total_val) > 0.01:
            all_warnings.append("Subtotal + tax ≠ total.")
            total_conf = 0.85
            subtotal_conf = 0.85
        else:
            total_conf = 0.98
            subtotal_conf = 0.98
            tax_conf = 0.98

    # Deduplicate warnings while preserving order
    unique_warnings: List[str] = []
    for w in all_warnings:
        if w not in unique_warnings:
            unique_warnings.append(w)

    return ExtractionResponse(
        invoice_number=inv_num_val,
        invoice_date=inv_date_val,
        due_date=due_date_val,
        subtotal=subtotal_val,
        tax=tax_val,
        total=total_val,
        currency=curr_res.currency,
        vendor=vendor_name,
        confidence=ConfidenceScores(
            invoice_number=round(inv_num_conf, 2),
            invoice_date=round(inv_date_conf, 2),
            due_date=round(due_date_conf, 2),
            subtotal=round(subtotal_conf, 2),
            tax=round(tax_conf, 2),
            total=round(total_conf, 2),
            currency=round(curr_res.confidence, 2),
            vendor=round(vendor_res.confidence, 2),
        ),
        warnings=unique_warnings
    )
