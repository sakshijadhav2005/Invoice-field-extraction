import re
from typing import List, Optional
from pydantic import BaseModel
from rapidfuzz import fuzz

LEGAL_SUFFIXES = [
    r'\bltd\.?\b', r'\blimited\b', r'\binc\.?\b', r'\bincorporated\b',
    r'\bllc\.?\b', r'\bgmbh\b', r'\bkk\.?\b', r'\bk\.k\.?\b', r'株式会社',
    r'\bpvt\.?\b', r'\bprivate\b', r'\bco\.?\b', r'\bcorp\.?\b', r'\bcorporation\b'
]

class VendorInfo(BaseModel):
    canonical_name: str
    country: str
    default_currency: str
    aliases: List[str]
    cities: List[str]
    tax_patterns: List[str]

CANONICAL_VENDORS: List[VendorInfo] = [
    VendorInfo(
        canonical_name="Northwind Traders",
        country="UK",
        default_currency="GBP",
        aliases=[
            "Northwind Traders", "NORTHWIND TRADERS LTD", "Northwind Traders Ltd",
            "Northwind Traders Limited", "Northwind Traders Inc"
        ],
        cities=["bristol", "quay street", "united kingdom", "uk"],
        tax_patterns=[r'\bGB\s*\d{3}\s*\d{4}\s*\d{2}\b', r'\bGB\d{9}\b', r'VAT\s*No\.?\s*GB']
    ),
    VendorInfo(
        canonical_name="Blue Harbour Logistics",
        country="UK",
        default_currency="GBP",
        aliases=[
            "Blue Harbour Logistics", "Blue Harbor Logistics", "Blue Harbour Logistics Ltd",
            "Blue Harbor Logistics Inc", "Harbour Engineering Ltd", "Harbour Engineering", "Harbor Engineering"
        ],
        cities=["bristol", "bath", "london", "united kingdom", "uk"],
        tax_patterns=[r'\bGB\d{9}\b', r'VAT\s*No\.?\s*GB']
    ),
    VendorInfo(
        canonical_name="Kestrel Components",
        country="US",
        default_currency="USD",
        aliases=[
            "Kestrel Components", "Kestrel Components Inc.", "Kestrel Components Inc",
            "Kestrel Components LLC", "KESTREL COMPONENTS INC"
        ],
        cities=["dayton", "ohio", "oh", "industrial pkwy", "usa", "united states"],
        tax_patterns=[r'\bEIN\s*\d{2}-\d{7}\b', r'\b\d{2}-\d{7}\b']
    ),
    VendorInfo(
        canonical_name="Meridian Industrial",
        country="DE",
        default_currency="EUR",
        aliases=[
            "Meridian Industrial", "Meridian Industrial GmbH", "Meridan Industrial",
            "Meridan Industrial GmbH", "MERIDIAN INDUSTRIAL GMBH"
        ],
        cities=["berlin", "munich", "germany", "deutschland"],
        tax_patterns=[r'\bDE\d{9}\b', r'USt-IdNr']
    ),
    VendorInfo(
        canonical_name="Sakura Precision",
        country="JP",
        default_currency="JPY",
        aliases=[
            "Sakura Precision", "Sakura Precision K.K.", "Sakura Precision KK",
            "Sakura Precison", "Sakura Precision Co., Ltd.", "サクラプレシジョン"
        ],
        cities=["tokyo", "osaka", "japan", "日本"],
        tax_patterns=[r'\bT\d{13}\b']
    ),
    VendorInfo(
        canonical_name="Pinecrest Packaging",
        country="IN",
        default_currency="INR",
        aliases=[
            "Pinecrest Packaging", "Pinecrest Packaging Pvt Ltd", "Pinecrest Packaging Private Limited",
            "Pinecrest Packaging Ltd", "Apex Systems Pvt Ltd", "Apex Systems"
        ],
        cities=["bengaluru", "bangalore", "mumbai", "pune", "india"],
        tax_patterns=[r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z0-9]{3}\b', r'GSTIN']
    )
]

class VendorResult(BaseModel):
    canonical_name: str
    country: Optional[str] = None
    default_currency: Optional[str] = None
    confidence: float = 1.0
    warnings: List[str] = []

def normalize_vendor_name(name: str) -> str:
    """
    Normalizes a company name:
    - lowercase
    - strip punctuation
    - British/American spelling fold: harbor -> harbour
    - strip legal suffixes (Ltd, Inc, GmbH, KK, Pvt, etc.)
    - collapse whitespace
    """
    if not name:
        return ""

    s = name.lower()
    # British/American spelling folding
    s = s.replace("harbor", "harbour")
    
    # Strip legal suffixes
    for suf in LEGAL_SUFFIXES:
        s = re.sub(suf, ' ', s, flags=re.IGNORECASE)

    # Strip non-alphanumeric except spaces
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def match_vendor(document_text: str) -> VendorResult:
    """
    Identifies vendor using rapidfuzz against canonical vendor list and aliases.
    Excludes Bruviti customer names (Bill to / Sold to Bruviti).
    Checks secondary evidence (cities, tax-id patterns).
    """
    if not document_text or not document_text.strip():
        return VendorResult(
            canonical_name="unknown",
            country=None,
            default_currency=None,
            confidence=0.0,
            warnings=["Vendor name not in the canonical list."]
        )

    lines = document_text.splitlines()
    # Remove lines referring to customer (Bruviti)
    cleaned_lines = []
    for line in lines:
        if "bruviti" in line.lower():
            continue
        cleaned_lines.append(line.strip())

    cleaned_text = "\n".join(cleaned_lines)
    text_lower = cleaned_text.lower()

    best_vendor: Optional[VendorInfo] = None
    best_score = 0.0

    for vendor in CANONICAL_VENDORS:
        # Check canonical name and all aliases
        names_to_check = [vendor.canonical_name] + vendor.aliases
        vendor_max_score = 0.0

        for candidate_name in names_to_check:
            norm_candidate = normalize_vendor_name(candidate_name)

            # 1. Check in full cleaned text using partial ratio & token set ratio
            token_score = fuzz.token_set_ratio(norm_candidate, normalize_vendor_name(cleaned_text))
            partial_score = fuzz.partial_ratio(norm_candidate, normalize_vendor_name(cleaned_text))
            combo_score = 0.6 * token_score + 0.4 * partial_score

            # 2. Check line by line (especially header lines)
            for line in cleaned_lines[:15]:
                norm_line = normalize_vendor_name(line)
                if not norm_line:
                    continue
                line_score = fuzz.token_sort_ratio(norm_candidate, norm_line)
                if line_score > combo_score:
                    combo_score = line_score

            if combo_score > vendor_max_score:
                vendor_max_score = combo_score

        # 3. Boost score with secondary evidence (cities, tax patterns) only if base name matches reasonably
        if vendor_max_score >= 60.0:
            for city in vendor.cities:
                if re.search(rf'\b{city}\b', text_lower):
                    vendor_max_score += 8.0
                    break

            for tax_pat in vendor.tax_patterns:
                if re.search(tax_pat, cleaned_text, re.IGNORECASE):
                    vendor_max_score += 15.0
                    break

        if vendor_max_score > best_score:
            best_score = vendor_max_score
            best_vendor = vendor

    # Threshold: at least 75
    if best_vendor and best_score >= 75.0:
        conf = min(1.0, 0.70 + (best_score - 75.0) / 100.0)
        return VendorResult(
            canonical_name=best_vendor.canonical_name,
            country=best_vendor.country,
            default_currency=best_vendor.default_currency,
            confidence=round(conf, 2),
            warnings=[]
        )

    return VendorResult(
        canonical_name="unknown",
        country=None,
        default_currency=None,
        confidence=0.20,
        warnings=["Vendor name not in the canonical list."]
    )
