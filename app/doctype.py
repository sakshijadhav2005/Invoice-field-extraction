import re
from typing import List
from pydantic import BaseModel

class DocTypeResult(BaseModel):
    doc_type: str  # invoice, quotation, delivery_note, statement, credit_note, pro_forma, unknown
    is_invoice: bool
    warnings: List[str] = []

NON_INVOICE_PATTERNS = [
    ("quotation", r'\b(?:quotation|quote|estimate|cost\s*estimate|kostenvoranschlag|見積書)\b'),
    ("delivery_note", r'\b(?:delivery\s*note|packing\s*slip|lieferschein|納品書)\b'),
    ("statement", r'\b(?:statement\s*of\s*account|account\s*statement|kontoauszug)\b'),
    ("credit_note", r'\b(?:credit\s*note|credit\s*memo|gutschrift)\b'),
    ("pro_forma", r'\b(?:pro\s*[-]?\s*forma)\b'),
]

INVOICE_PATTERNS = r'\b(?:tax\s*invoice|commercial\s*invoice|invoice|rechnung|請求書|bill\s*to)\b'

def classify_document(text: str) -> DocTypeResult:
    """
    Classifies whether the document is an invoice or a non-invoice document
    (quotation, delivery note, statement, credit note, pro-forma).
    Implements Rule O4:
    Non-invoice documents result in all extraction fields null, vendor as found,
    with a warning naming the document type.
    """
    if not text:
        return DocTypeResult(
            doc_type="unknown",
            is_invoice=False,
            warnings=["Document is empty or unreadable."]
        )

    # Inspect the top 20 lines / header text first
    header_text = "\n".join(text.splitlines()[:20]).lower()

    # 1. Check non-invoice patterns
    for dtype, pattern in NON_INVOICE_PATTERNS:
        if re.search(pattern, header_text, re.IGNORECASE):
            human_name = dtype.replace("_", " ")
            return DocTypeResult(
                doc_type=dtype,
                is_invoice=False,
                warnings=[f"Document is a {human_name} (not a valid tax invoice)."]
            )

    # 2. Check invoice patterns
    if re.search(INVOICE_PATTERNS, header_text, re.IGNORECASE):
        return DocTypeResult(
            doc_type="invoice",
            is_invoice=True,
            warnings=[]
        )

    # Check anywhere in text
    for dtype, pattern in NON_INVOICE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            human_name = dtype.replace("_", " ")
            return DocTypeResult(
                doc_type=dtype,
                is_invoice=False,
                warnings=[f"Document is a {human_name} (not a valid tax invoice)."]
            )

    # Default to invoice if generic
    return DocTypeResult(
        doc_type="invoice",
        is_invoice=True,
        warnings=[]
    )
