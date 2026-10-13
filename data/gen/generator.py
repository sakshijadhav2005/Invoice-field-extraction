import os
import random
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

CANONICAL_VENDORS_DATA = [
    {
        "name": "Northwind Traders",
        "country": "UK",
        "currency": "GBP",
        "symbol": "£",
        "city": "14 Quay Street, Bristol BS1 4DB, United Kingdom",
        "tax_id": "VAT No. GB 123 4567 89",
        "noise_names": ["NORTHWIND TRADERS LTD", "Northwind Traders", "Northwind Traders Ltd", "Northwind Traders Limited"]
    },
    {
        "name": "Blue Harbour Logistics",
        "country": "UK",
        "currency": "GBP",
        "symbol": "£",
        "city": "Bristol, UK",
        "tax_id": "VAT No GB987654321",
        "noise_names": ["Blue Harbour Logistics", "Blue Harbor Logistics", "Blue Harbour Logistics Ltd", "Blue Harbor Logistics Inc"]
    },
    {
        "name": "Kestrel Components",
        "country": "US",
        "currency": "USD",
        "symbol": "$",
        "city": "880 Industrial Pkwy, Dayton OH 45402, USA",
        "tax_id": "EIN 31-1234567",
        "noise_names": ["Kestrel Components Inc.", "Kestrel Components", "Kestrel Components LLC", "KESTREL COMPONENTS INC"]
    },
    {
        "name": "Meridian Industrial",
        "country": "DE",
        "currency": "EUR",
        "symbol": "€",
        "city": "Berlin, Germany",
        "tax_id": "USt-IdNr DE987654321",
        "noise_names": ["Meridian Industrial GmbH", "Meridan Industrial GmbH", "Meridian Industrial", "MERIDIAN INDUSTRIAL GMBH"]
    },
    {
        "name": "Sakura Precision",
        "country": "JP",
        "currency": "JPY",
        "symbol": "¥",
        "city": "Tokyo, Japan",
        "tax_id": "T1234567890123",
        "noise_names": ["Sakura Precision K.K.", "Sakura Precision", "Sakura Precison KK", "Sakura Precision Co., Ltd."]
    },
    {
        "name": "Pinecrest Packaging",
        "country": "IN",
        "currency": "INR",
        "symbol": "₹",
        "city": "Bengaluru, India",
        "tax_id": "GSTIN 29AAAAA0000A1Z5",
        "noise_names": ["Pinecrest Packaging Pvt Ltd", "Pinecrest Packaging", "Pinecrest Packaging Private Limited", "Pinecrest Packaging Ltd"]
    }
]

UNKNOWN_VENDORS_DATA = [
    {"name": "Quantum Matrix Logistics", "country": "US", "currency": "USD", "symbol": "$", "city": "Chicago, USA"},
    {"name": "Nordic Flow Supplies AB", "country": "SE", "currency": "EUR", "symbol": "€", "city": "Stockholm, Sweden"},
    {"name": "Pacific Horizon Traders", "country": "AU", "currency": "USD", "symbol": "$", "city": "Sydney, Australia"},
    {"name": "Alpine Peak Manufacturing", "country": "CH", "currency": "EUR", "symbol": "€", "city": "Zurich, Switzerland"},
]

MONTH_NAMES_LIST = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_FULL_LIST = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def _format_date(y: int, m: int, d: int, style: str) -> str:
    if style == "iso":
        return f"{y:04d}-{m:02d}-{d:02d}"
    elif style == "uk_slash":
        return f"{d:02d}/{m:02d}/{y:04d}"
    elif style == "us_slash":
        return f"{m:02d}/{d:02d}/{y:04d}"
    elif style == "de_dot":
        return f"{d:02d}.{m:02d}.{y:04d}"
    elif style == "text_d_mon_y":
        return f"{d} {MONTH_NAMES_LIST[m-1]} {y}"
    elif style == "text_mon_d_y":
        return f"{MONTH_FULL_LIST[m-1]} {d}, {y}"
    elif style == "text_ordinal":
        suffix = "th" if 11 <= d <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
        return f"{d}{suffix} {MONTH_NAMES_LIST[m-1]} {y}"
    elif style == "dash_short":
        return f"{d:02d}-{MONTH_NAMES_LIST[m-1]}-{str(y)[2:]}"
    elif style == "jp_dot":
        return f"{y:04d}.{m:02d}.{d:02d}"
    elif style == "jp_slash":
        return f"{y:04d}/{m:02d}/{d:02d}"
    return f"{y:04d}-{m:02d}-{d:02d}"

def _format_money(amount: float, locale_style: str, currency_symbol: str, currency_code: str, currency_mode: str) -> str:
    if locale_style == "de":
        # 1.234,56
        s = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    elif locale_style == "in":
        # Indian lakh grouping or standard comma
        s = f"{amount:,.2f}"
    elif locale_style == "jp":
        s = f"{int(amount):,}"
    else:
        s = f"{amount:,.2f}"

    if currency_mode == "symbol":
        return f"{currency_symbol}{s}"
    elif currency_mode == "symbol_space":
        return f"{currency_symbol} {s}"
    elif currency_mode == "code":
        return f"{s} {currency_code}"
    elif currency_mode == "both":
        return f"{currency_symbol}{s} {currency_code}"
    else: # none
        return s

def generate_invoice_sample(
    index: int,
    output_dir: Path,
    is_holdout: bool = False,
    doc_type_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a single synthetic invoice PDF and its ground truth JSON.
    Varies vendors, dates, layout geometry, labels, terms, tax schemes, and arithmetic.
    """
    random.seed(1000 + index * 17)
    
    # 1. Vendor selection
    is_unknown = (index % 7 == 0) and not is_holdout
    if is_unknown:
        vendor_data = random.choice(UNKNOWN_VENDORS_DATA)
        canonical_vendor = "unknown"
        printed_name = vendor_data["name"]
    else:
        vendor_data = random.choice(CANONICAL_VENDORS_DATA)
        canonical_vendor = vendor_data["name"]
        printed_name = random.choice(vendor_data["noise_names"])

    country = vendor_data["country"]
    currency_code = vendor_data["currency"]
    currency_symbol = vendor_data["symbol"]

    # 2. Document type (Rule O4)
    doc_type = doc_type_override or ("quotation" if index % 19 == 0 else "invoice")

    # 3. Invoice Number
    prefix = random.choice(["INV", "KC", "RE", "BL", "DOC", "REF"])
    inv_num_val = f"{prefix}-{2026}-{1000 + index}"

    # 4. Dates
    inv_yr, inv_m, inv_d = 2026, random.randint(1, 12), random.randint(1, 28)
    inv_date_iso = f"{inv_yr:04d}-{inv_m:02d}-{inv_d:02d}"

    # Select date format by country
    if country == "US":
        date_styles = ["us_slash", "text_mon_d_y", "iso"]
    elif country == "DE":
        date_styles = ["de_dot", "iso"]
    elif country == "JP":
        date_styles = ["jp_dot", "jp_slash", "iso"]
    elif country == "IN":
        date_styles = ["uk_slash", "text_ordinal", "dash_short"]
    else: # UK
        date_styles = ["uk_slash", "text_d_mon_y", "dash_short"]
    
    date_style = random.choice(date_styles)
    inv_date_str = _format_date(inv_yr, inv_m, inv_d, date_style)

    # 5. Terms vs Due Date (Rule O1)
    terms_mode = random.choice(["printed_only", "terms_only", "both_agree", "both_disagree", "due_on_receipt"])
    due_days = random.choice([14, 30, 45, 60])
    
    from datetime import date, timedelta
    inv_dt = date(inv_yr, inv_m, inv_d)
    derived_due_dt = inv_dt + timedelta(days=due_days)
    derived_due_iso = derived_due_dt.isoformat()

    printed_due_str: Optional[str] = None
    terms_str: Optional[str] = None
    expected_due_iso: Optional[str] = None

    if terms_mode == "printed_only":
        printed_due_str = _format_date(derived_due_dt.year, derived_due_dt.month, derived_due_dt.day, date_style)
        expected_due_iso = derived_due_iso
    elif terms_mode == "terms_only":
        terms_str = f"Net {due_days}"
        expected_due_iso = derived_due_iso
    elif terms_mode == "both_agree":
        printed_due_str = _format_date(derived_due_dt.year, derived_due_dt.month, derived_due_dt.day, date_style)
        terms_str = f"Payment within {due_days} days"
        expected_due_iso = derived_due_iso
    elif terms_mode == "both_disagree":
        # Disagree: printed is 10 days earlier
        disagree_dt = derived_due_dt - timedelta(days=10)
        printed_due_str = _format_date(disagree_dt.year, disagree_dt.month, disagree_dt.day, date_style)
        terms_str = f"Net {due_days}"
        expected_due_iso = disagree_dt.isoformat()  # Rule O1: printed due date wins
    elif terms_mode == "due_on_receipt":
        terms_str = "Due on receipt"
        expected_due_iso = None

    # 6. Currency Mode (Rule O3)
    curr_mode = random.choice(["symbol", "code", "both", "none"])
    if is_unknown and curr_mode == "none":
        expected_currency = None
    else:
        expected_currency = currency_code  # Rule O3 fallback to vendor currency if none

    # 7. Amounts
    locale_style = "de" if country == "DE" else ("jp" if country == "JP" else ("in" if country == "IN" else "us"))
    base_subtotal = float(random.randint(50, 500) * 10)
    tax_rate = random.choice([0.0, 0.05, 0.10, 0.18, 0.20])
    base_tax = round(base_subtotal * tax_rate, 2)
    
    if locale_style == "jp":
        base_subtotal = float(int(base_subtotal))
        base_tax = float(int(base_tax))
    
    # Arithmetic mismatch (Rule O2)
    mismatch_arithmetic = (index % 23 == 0) and not is_holdout
    if mismatch_arithmetic:
        base_total = round(base_subtotal + base_tax + 50.00, 2)
    else:
        base_total = round(base_subtotal + base_tax, 2)

    subtotal_str = _format_money(base_subtotal, locale_style, currency_symbol, currency_code, curr_mode)
    tax_str = _format_money(base_tax, locale_style, currency_symbol, currency_code, curr_mode)
    total_str = _format_money(base_total, locale_style, currency_symbol, currency_code, curr_mode)

    # 8. Render PDF with reportlab
    pdf_filename = f"inv_{index:04d}.pdf"
    json_filename = f"inv_{index:04d}.json"
    pdf_path = output_dir / pdf_filename
    json_path = output_dir / json_filename

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    
    # Customer name: Bruviti Services Pvt Ltd
    customer_line = "Bill To: Bruviti Services Pvt Ltd, Tech Park, Pune"

    # Select layout family (6 layout families)
    layout = index % 6

    # Draw header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, printed_name)
    c.setFont("Helvetica", 9)
    if "city" in vendor_data:
        c.drawString(50, 735, vendor_data["city"])
    if "tax_id" in vendor_data:
        c.drawString(50, 720, vendor_data["tax_id"])

    doc_title = "TAX INVOICE" if doc_type == "invoice" else doc_type.upper()
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(550, 750, doc_title)

    c.setFont("Helvetica", 9)
    c.drawString(50, 690, customer_line)

    # Labels variations
    inv_no_label = random.choice(["Invoice No:", "Invoice #:", "Reference No:", "Inv. No.:", "Rechnungsnr.:", "Bill No.:"])
    date_label = random.choice(["Invoice Date:", "Date of Issue:", "Dated:", "Rechnungsdatum:", "Date:"])
    due_label = random.choice(["Due Date:", "Payment Due:", "Pay By:", "Fällig am:"])
    sub_label = random.choice(["Subtotal:", "Sub Total:", "Net Amount:", "Nettobetrag:"])
    tax_label = f"VAT ({int(tax_rate*100)}%):" if tax_rate > 0 else "Tax:"
    tot_label = random.choice(["Total Due:", "Grand Total:", "Balance Due:", "Total:", "Gesamtbetrag:"])

    # Draw layout elements
    if layout == 0:
        # Standard two-column details
        c.drawString(50, 650, f"{inv_no_label} {inv_num_val}")
        c.drawString(50, 635, f"{date_label} {inv_date_str}")
        if printed_due_str:
            c.drawString(50, 620, f"{due_label} {printed_due_str}")
        if terms_str:
            c.drawString(50, 605, f"Terms: {terms_str}")

        # Totals box bottom-right
        c.drawString(380, 520, f"{sub_label} {subtotal_str}")
        c.drawString(380, 500, f"{tax_label} {tax_str}")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(380, 480, f"{tot_label} {total_str}")

    elif layout == 1:
        # Right-aligned header block
        c.drawRightString(550, 690, f"{inv_no_label} {inv_num_val}")
        c.drawRightString(550, 675, f"{date_label} {inv_date_str}")
        if printed_due_str:
            c.drawRightString(550, 660, f"{due_label} {printed_due_str}")
        if terms_str:
            c.drawRightString(550, 645, f"Payment Terms: {terms_str}")

        c.drawRightString(550, 480, f"{sub_label} {subtotal_str}")
        c.drawRightString(550, 460, f"{tax_label} {tax_str}")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(550, 440, f"{tot_label} {total_str}")

    elif layout == 2:
        # Label above value
        c.drawString(50, 660, inv_no_label)
        c.drawString(50, 645, inv_num_val)
        c.drawString(200, 660, date_label)
        c.drawString(200, 645, inv_date_str)
        if printed_due_str:
            c.drawString(350, 660, due_label)
            c.drawString(350, 645, printed_due_str)

        if terms_str:
            c.drawString(50, 615, f"Terms: {terms_str}")

        c.drawString(380, 480, f"{sub_label} {subtotal_str}")
        c.drawString(380, 460, f"{tax_label} {tax_str}")
        c.drawString(380, 440, f"{tot_label} {total_str}")

    elif layout == 3:
        # Two-column box with border line
        c.line(50, 670, 550, 670)
        c.drawString(55, 655, f"{inv_no_label} {inv_num_val}")
        c.drawString(320, 655, f"{date_label} {inv_date_str}")
        if printed_due_str:
            c.drawString(320, 640, f"{due_label} {printed_due_str}")
        if terms_str:
            c.drawString(55, 640, f"Terms: {terms_str}")
        c.line(50, 630, 550, 630)

        c.drawString(380, 500, f"{sub_label} {subtotal_str}")
        c.drawString(380, 480, f"{tax_label} {tax_str}")
        c.drawString(380, 460, f"{tot_label} {total_str}")

    elif layout == 4:
        # Simulated line item table with headers
        c.drawString(50, 650, f"{inv_no_label} {inv_num_val}")
        c.drawString(50, 635, f"{date_label} {inv_date_str}")
        if printed_due_str:
            c.drawString(50, 620, f"{due_label} {printed_due_str}")
        if terms_str:
            c.drawString(50, 605, f"Terms: {terms_str}")

        # Table header: Item | Qty | Rate | Line Total
        c.line(50, 570, 550, 570)
        c.drawString(55, 558, "Description")
        c.drawString(320, 558, "Qty")
        c.drawString(400, 558, "Rate")
        c.drawRightString(545, 558, "Amount")
        c.line(50, 550, 550, 550)

        # Line items
        c.drawString(55, 535, "Industrial component assemblies")
        c.drawString(320, 535, "1")
        c.drawString(400, 535, subtotal_str)
        c.drawRightString(545, 535, subtotal_str)
        c.line(50, 520, 550, 520)

        c.drawRightString(545, 490, f"{sub_label} {subtotal_str}")
        c.drawRightString(545, 470, f"{tax_label} {tax_str}")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(545, 450, f"{tot_label} {total_str}")

    else:
        # Multi-page invoice (Page 1 items, Page 2 totals)
        c.drawString(50, 650, f"{inv_no_label} {inv_num_val}")
        c.drawString(50, 635, f"{date_label} {inv_date_str}")
        if printed_due_str:
            c.drawString(50, 620, f"{due_label} {printed_due_str}")
        if terms_str:
            c.drawString(50, 605, f"Terms: {terms_str}")
        c.drawString(50, 550, "Services rendered for Q3 maintenance.")
        c.drawString(50, 530, "(Continued on Page 2)")
        c.showPage()

        # Page 2
        c.drawString(50, 750, f"Invoice Reference: {inv_num_val} (Page 2)")
        c.drawRightString(550, 650, f"{sub_label} {subtotal_str}")
        c.drawRightString(550, 630, f"{tax_label} {tax_str}")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(550, 610, f"{tot_label} {total_str}")

    c.showPage()
    c.save()

    # Build ground truth JSON
    if doc_type != "invoice":
        # Rule O4: Non-invoice doc has null fields, vendor as found
        ground_truth = {
            "vendor": canonical_vendor,
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "subtotal": None,
            "tax": None,
            "total": None,
            "currency": None,
            "doc_type": doc_type
        }
    else:
        ground_truth = {
            "vendor": canonical_vendor,
            "invoice_number": inv_num_val,
            "invoice_date": inv_date_iso,
            "due_date": expected_due_iso,
            "subtotal": base_subtotal,
            "tax": base_tax,
            "total": base_total,
            "currency": expected_currency,
            "doc_type": "invoice"
        }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    return ground_truth
