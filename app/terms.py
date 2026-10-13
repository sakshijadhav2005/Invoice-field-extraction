import re
from datetime import date, timedelta
from typing import List, Optional
from pydantic import BaseModel

class DueDateResult(BaseModel):
    due_date_iso: Optional[str] = None
    confidence: float = 1.0
    warnings: List[str] = []

def extract_terms_days(text: str) -> Optional[int]:
    """
    Extracts payment term days from strings like:
    'Net 30', 'Net30', 'N30', '30 days', 'Payment within 30 days',
    'due in 14 days', 'Terms: 45', '2/10 Net 30'
    Returns integer days or None.
    """
    if not text or not text.strip():
        return None

    s = text.strip()

    # Discount terms e.g. 2/10 Net 30 -> extract 30
    discount_match = re.search(r'\d+/\d+\s+Net\s*(\d+)', s, re.IGNORECASE)
    if discount_match:
        return int(discount_match.group(1))

    # Net N / NetN / N30
    net_match = re.search(r'\b(?:Net\s*|N)(\d{1,3})\b', s, re.IGNORECASE)
    if net_match:
        return int(net_match.group(1))

    # N days / Payment within N days / due in N days
    days_match = re.search(r'\b(?:within\s+|in\s+)?(\d{1,3})\s*days\b', s, re.IGNORECASE)
    if days_match:
        return int(days_match.group(1))

    # Terms: N
    terms_match = re.search(r'\bTerms:\s*(\d{1,3})\b', s, re.IGNORECASE)
    if terms_match:
        return int(terms_match.group(1))

    return None

def resolve_due_date(
    invoice_date_iso: Optional[str],
    printed_due_date_iso: Optional[str],
    terms_text: Optional[str]
) -> DueDateResult:
    """
    Implements Rule O1:
    - If printed due date exists and terms exist, check for consistency.
      If they disagree, use the printed date and add a warning.
    - If only terms exist and invoice date is known, derive due_date = invoice_date + N days
      and add warning 'Due date derived from terms Net N.'
    - If 'Due on receipt' / 'Immediate', leave due_date as null with a warning.
    """
    warnings: List[str] = []
    
    # Check for "Due on receipt" / "Immediate"
    if terms_text and re.search(r'\b(?:due\s+on\s+receipt|immediate)\b', terms_text, re.IGNORECASE):
        if not printed_due_date_iso:
            return DueDateResult(
                due_date_iso=None,
                confidence=0.0,
                warnings=[f"Payment term '{terms_text}' specified; no calendar due date."]
            )

    days = extract_terms_days(terms_text or "")
    derived_due_date = None

    if days is not None and invoice_date_iso:
        try:
            inv_d = date.fromisoformat(invoice_date_iso)
            derived_d = inv_d + timedelta(days=days)
            derived_due_date = derived_d.isoformat()
        except ValueError:
            pass

    # Case 1: Printed due date exists
    if printed_due_date_iso:
        if derived_due_date and derived_due_date != printed_due_date_iso:
            warnings.append(
                f"Printed due date {printed_due_date_iso} and payment terms '{terms_text}' disagree."
            )
        return DueDateResult(
            due_date_iso=printed_due_date_iso,
            confidence=0.95,
            warnings=warnings
        )

    # Case 2: Only derived due date exists
    if derived_due_date:
        matched_term = f"Net {days}" if not terms_text or "net" in terms_text.lower() else terms_text
        warnings.append(f"Due date derived from terms {matched_term}.")
        return DueDateResult(
            due_date_iso=derived_due_date,
            confidence=0.90,
            warnings=warnings
        )

    # Case 3: Neither exists
    return DueDateResult(due_date_iso=None, confidence=0.0, warnings=[])
