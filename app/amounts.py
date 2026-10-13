import re
from typing import Optional

CURRENCY_SYMBOLS_PATTERN = r'[$£€¥₹]|(?:Rs\.?)|(?:INR|USD|EUR|GBP|JPY)\b'

def parse_amount(text: str) -> Optional[float]:
    """
    Parses an amount string across multiple currency formats and locales:
    - Standard US/UK: 1,234.56
    - German/EU: 1.234,56
    - Indian numbering: 1,23,456.00
    - Japanese Yen: 12,000 or 12000 (Rule O5: always outputs 2 decimal places)
    - Rejects percentages (e.g. 20%, 7.25%)
    - Handles negative numbers: -150.00, (150.00), 150.00-
    """
    if not text or not text.strip():
        return None

    s = text.strip()

    # Reject percentages immediately
    if '%' in s:
        return None

    # Check for negative sign
    is_negative = False
    if s.startswith('(') and s.endswith(')'):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith('-'):
        is_negative = True
        s = s[1:].strip()
    elif s.endswith('-'):
        is_negative = True
        s = s[:-1].strip()

    # Strip currency symbols and codes
    s = re.sub(CURRENCY_SYMBOLS_PATTERN, '', s, flags=re.IGNORECASE).strip()

    # Must contain at least one digit
    if not re.search(r'\d', s):
        return None

    # Strip any leading non-digit characters (e.g. font glyph substitutions like 'I')
    s = re.sub(r'^[^\d]+', '', s)
    # Strip any trailing non-digit characters
    s = re.sub(r'[^\d]+$', '', s)

    # Replace apostrophes and non-breaking spaces with standard space
    s = s.replace("'", " ").replace("\u00a0", " ").strip()

    # Find all separators (dots and commas)
    # Check if there are spaces used as thousand separators (e.g. "1 234,56")
    # If space is followed by digits and then comma/dot
    s_no_space = re.sub(r'(?<=\d)\s+(?=\d)', '', s)

    # Let's inspect dots and commas in s_no_space
    has_dot = '.' in s_no_space
    has_comma = ',' in s_no_space

    if has_dot and has_comma:
        # Both present: find the position of the last one
        last_dot = s_no_space.rfind('.')
        last_comma = s_no_space.rfind(',')

        if last_comma > last_dot:
            # European format: 1.234,56 -> dot is thousand sep, comma is decimal
            # Verify digits after comma
            after_comma = s_no_space[last_comma + 1:]
            if len(after_comma) in (1, 2):
                clean_str = s_no_space[:last_comma].replace('.', '') + '.' + after_comma
            else:
                clean_str = s_no_space.replace('.', '').replace(',', '')
        else:
            # US/UK/Indian format: 1,234.56 or 1,23,456.00 -> comma is thousand sep, dot is decimal
            after_dot = s_no_space[last_dot + 1:]
            if len(after_dot) in (1, 2):
                clean_str = s_no_space[:last_dot].replace(',', '') + '.' + after_dot
            else:
                clean_str = s_no_space.replace(',', '').replace('.', '')
    elif has_comma and not has_dot:
        # Only comma exists: e.g. "12,000" (thousand sep) or "123,45" (European decimal)
        last_comma = s_no_space.rfind(',')
        after_comma = s_no_space[last_comma + 1:]
        # If followed by exactly 2 digits, it's decimal: 123,45 -> 123.45
        if len(after_comma) == 2:
            clean_str = s_no_space[:last_comma] + '.' + after_comma
        elif len(after_comma) == 3:
            # e.g. 12,000 -> thousand separator
            clean_str = s_no_space.replace(',', '')
        elif len(after_comma) == 1:
            clean_str = s_no_space[:last_comma] + '.' + after_comma
        else:
            clean_str = s_no_space.replace(',', '')
    elif has_dot and not has_comma:
        # Only dot exists: e.g. "1234.56" (decimal) or "12.000" (German thousand sep)
        last_dot = s_no_space.rfind('.')
        after_dot = s_no_space[last_dot + 1:]
        # If there are multiple dots: e.g. "1.234.567" -> thousand seps
        if s_no_space.count('.') > 1:
            clean_str = s_no_space.replace('.', '')
        elif len(after_dot) in (1, 2):
            clean_str = s_no_space
        elif len(after_dot) == 3 and len(s_no_space[:last_dot]) <= 3:
            # Likely thousand sep e.g. 12.000 EUR
            clean_str = s_no_space.replace('.', '')
        else:
            clean_str = s_no_space
    else:
        # No dot and no comma: pure integer e.g. "12000"
        clean_str = s_no_space

    try:
        val = float(clean_str)
        if is_negative:
            val = -val
        return round(val, 2)
    except ValueError:
        return None

def format_amount_str(val: Optional[float]) -> Optional[str]:
    """
    Formats float to string with exactly two decimals, no thousand separators (e.g. 1234.56 or 12000.00).
    """
    if val is None:
        return None
    return f"{val:.2f}"
