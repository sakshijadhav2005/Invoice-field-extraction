import re
from typing import List, Optional
from pydantic import BaseModel

CURRENCY_MAP = {
    '£': 'GBP',
    '$': 'USD',
    '€': 'EUR',
    '¥': 'JPY',
    '円': 'JPY',
    '₹': 'INR',
    'rs.': 'INR',
    'rs': 'INR',
}

ISO_CODES = {'GBP', 'USD', 'EUR', 'JPY', 'INR'}

class CurrencyResult(BaseModel):
    currency: Optional[str] = None
    confidence: float = 1.0
    warnings: List[str] = []

def detect_currency_in_text(text: str) -> Optional[str]:
    """
    Scans text for currency symbols and ISO codes.
    Returns 3-letter ISO currency code or None.
    """
    if not text:
        return None

    # 1. Check for specific symbols first
    if '£' in text:
        return 'GBP'
    if '€' in text:
        return 'EUR'
    if '¥' in text or '円' in text:
        return 'JPY'
    if '₹' in text:
        return 'INR'
    if re.search(r'\bRs\.?\s*\d', text, re.IGNORECASE):
        return 'INR'
    if '$' in text:
        return 'USD'

    # 2. Check for explicit ISO 3-letter codes as whole words
    for code in ISO_CODES:
        if re.search(rf'\b{code}\b', text, re.IGNORECASE):
            return code

    return None

def resolve_currency(
    text: str,
    vendor_currency: Optional[str] = None
) -> CurrencyResult:
    """
    Resolves currency from extracted text and vendor default.
    Implements Rule O3:
    - If currency printed: use it. If it differs from vendor default, warn.
    - If currency not printed: fallback to vendor default with warning & confidence ~0.50.
    """
    warnings: List[str] = []
    detected = detect_currency_in_text(text)

    if detected:
        if vendor_currency and detected != vendor_currency:
            warnings.append(f"Printed currency {detected} differs from vendor default {vendor_currency}.")
        return CurrencyResult(
            currency=detected,
            confidence=0.98,
            warnings=warnings
        )

    # Fallback to vendor default (Rule O3)
    if vendor_currency:
        warnings.append("Currency not printed, vendor currency used.")
        return CurrencyResult(
            currency=vendor_currency,
            confidence=0.50,
            warnings=warnings
        )

    return CurrencyResult(
        currency=None,
        confidence=0.0,
        warnings=[]
    )
