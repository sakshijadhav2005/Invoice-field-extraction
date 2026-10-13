import re
from datetime import date
from typing import List, Optional
from pydantic import BaseModel

MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

class DateParseResult(BaseModel):
    raw_str: str
    iso_date: Optional[str] = None
    is_ambiguous: bool = False
    confidence: float = 1.0
    warnings: List[str] = []

def _normalize_year(y: int) -> int:
    if y < 100:
        return 2000 + y if y < 70 else 1900 + y
    return y

def _is_valid_date(y: int, m: int, d: int) -> bool:
    try:
        date(y, m, d)
        return True
    except (ValueError, OverflowError):
        return False

def parse_date(
    raw_str: str,
    country: Optional[str] = None,
    currency_hint: Optional[str] = None
) -> Optional[DateParseResult]:
    """
    Parses a date string into an ISO YYYY-MM-DD format based on vendor country rules.
    Ambiguous numeric dates (e.g. 9/3/26 or 03/09/2026 where both parts <= 12)
    are resolved based on country: US is month-first, UK/DE/JP/IN are day-first.
    """
    if not raw_str or not raw_str.strip():
        return None

    s = raw_str.strip()
    warnings = []

    # 1. Japanese Kanji Era: 令和8年9月3日 (Reiwa 8 = 2026)
    reiwa_match = re.search(r'令和\s*(\d{1,2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', s)
    if reiwa_match:
        era_yr, m, d = int(reiwa_match.group(1)), int(reiwa_match.group(2)), int(reiwa_match.group(3))
        y = 2018 + era_yr
        if _is_valid_date(y, m, d):
            return DateParseResult(raw_str=s, iso_date=f"{y:04d}-{m:02d}-{d:02d}", is_ambiguous=False, confidence=0.98)

    # 2. Japanese Kanji YYYY年MM月DD日
    kanji_match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', s)
    if kanji_match:
        y, m, d = int(kanji_match.group(1)), int(kanji_match.group(2)), int(kanji_match.group(3))
        if _is_valid_date(y, m, d):
            return DateParseResult(raw_str=s, iso_date=f"{y:04d}-{m:02d}-{d:02d}", is_ambiguous=False, confidence=0.98)

    # 3. ISO / Year-first numeric: YYYY-MM-DD or YYYY.MM.DD or YYYY/MM/DD
    iso_match = re.search(r'\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b', s)
    if iso_match:
        y, m, d = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
        if _is_valid_date(y, m, d):
            return DateParseResult(raw_str=s, iso_date=f"{y:04d}-{m:02d}-{d:02d}", is_ambiguous=False, confidence=0.98)

    # 4. Textual month formats:
    # 4a. Day Month Year: e.g. "3 Sep 2026", "3rd September 2026", "03-Sep-26"
    day_month_match = re.search(
        r'\b(\d{1,2})(?:st|nd|rd|th)?[-/\s]+([A-Za-z]+)[-/\s]+(\d{2,4})\b',
        s,
        re.IGNORECASE
    )
    if day_month_match:
        d = int(day_month_match.group(1))
        m_str = day_month_match.group(2).lower()
        y = _normalize_year(int(day_month_match.group(3)))
        if m_str in MONTH_NAMES:
            m = MONTH_NAMES[m_str]
            if _is_valid_date(y, m, d):
                return DateParseResult(raw_str=s, iso_date=f"{y:04d}-{m:02d}-{d:02d}", is_ambiguous=False, confidence=0.98)

    # 4b. Month Day Year: e.g. "September 3, 2026", "Sep 3 26"
    month_day_match = re.search(
        r'\b([A-Za-z]+)[-/\s]+(\d{1,2})(?:st|nd|rd|th)?(?:,)?[-/\s]+(\d{2,4})\b',
        s,
        re.IGNORECASE
    )
    if month_day_match:
        m_str = month_day_match.group(1).lower()
        d = int(month_day_match.group(2))
        y = _normalize_year(int(month_day_match.group(3)))
        if m_str in MONTH_NAMES:
            m = MONTH_NAMES[m_str]
            if _is_valid_date(y, m, d):
                return DateParseResult(raw_str=s, iso_date=f"{y:04d}-{m:02d}-{d:02d}", is_ambiguous=False, confidence=0.98)

    # 5. Pure numeric formats: Part1 / Part2 / Year
    # e.g. 03/09/2026, 9/3/26, 03.09.2026, 03-09-2026
    num_match = re.search(r'\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b', s)
    if num_match:
        p1 = int(num_match.group(1))
        p2 = int(num_match.group(2))
        y = _normalize_year(int(num_match.group(3)))

        # Unambiguous case 1: p1 > 12 -> p1 must be day, p2 must be month
        if p1 > 12 and p2 <= 12:
            if _is_valid_date(y, p2, p1):
                return DateParseResult(raw_str=s, iso_date=f"{y:04d}-{p2:02d}-{p1:02d}", is_ambiguous=False, confidence=0.95)
            return None

        # Unambiguous case 2: p2 > 12 -> p2 must be day, p1 must be month
        if p2 > 12 and p1 <= 12:
            if _is_valid_date(y, p1, p2):
                return DateParseResult(raw_str=s, iso_date=f"{y:04d}-{p1:02d}-{p2:02d}", is_ambiguous=False, confidence=0.95)
            return None

        # Both p1 <= 12 and p2 <= 12: Ambiguous!
        if p1 <= 12 and p2 <= 12:
            # Determine country convention
            country_norm = (country or "").strip().upper()
            is_us = False

            if country_norm in ("US", "USA"):
                is_us = True
                reading = "month-first (US vendor)"
            elif country_norm in ("UK", "GB", "DE", "JP", "IN"):
                is_us = False
                reading = f"day-first ({country_norm} vendor)"
            else:
                # Unknown vendor -> currency hint
                curr = (currency_hint or "").strip().upper()
                if curr == "USD":
                    is_us = True
                    reading = "month-first (USD hint)"
                else:
                    is_us = False
                    reading = "day-first (fallback)"

            if is_us:
                # Month-first: p1 is month, p2 is day
                m, d = p1, p2
            else:
                # Day-first: p1 is day, p2 is month
                d, m = p1, p2

            if _is_valid_date(y, m, d):
                warning_msg = f"Date {s} read as {reading}."
                return DateParseResult(
                    raw_str=s,
                    iso_date=f"{y:04d}-{m:02d}-{d:02d}",
                    is_ambiguous=True,
                    confidence=0.80 if country_norm in ("US", "UK", "GB", "DE", "JP", "IN") else 0.70,
                    warnings=[warning_msg]
                )

    return None
