import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.gen.generator import generate_invoice_sample
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import json

def generate_appendix_n_invoices(output_dir: Path):
    """
    Creates the golden reference invoices matching Examples 1, 2, and 3 from Appendix N.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Example 1: Northwind Traders
    pdf_1 = output_dir / "appendix_n_example_1.pdf"
    json_1 = output_dir / "appendix_n_example_1.json"
    
    c1 = canvas.Canvas(str(pdf_1), pagesize=letter)
    c1.setFont("Helvetica-Bold", 14)
    c1.drawString(50, 750, "NORTHWIND TRADERS LTD")
    c1.setFont("Helvetica", 9)
    c1.drawString(50, 735, "14 Quay Street, Bristol BS1 4DB, United Kingdom")
    c1.drawString(50, 720, "VAT No. GB 123 4567 89")
    
    c1.setFont("Helvetica-Bold", 14)
    c1.drawString(50, 690, "INVOICE")
    
    c1.setFont("Helvetica", 9)
    c1.drawString(50, 665, "Invoice No: NW-1042")
    c1.drawString(50, 650, "Invoice Date: 03/09/2026")
    c1.drawString(50, 635, "Due Date: 03/10/2026")
    c1.drawString(50, 620, "Bill to: Bruviti Services Pvt Ltd")
    
    # Table header
    c1.drawString(50, 580, "Item")
    c1.drawString(250, 580, "Qty")
    c1.drawString(340, 580, "Unit Price")
    c1.drawRightString(550, 580, "Amount")
    
    # Line items
    c1.drawString(50, 560, "Pallet wrap, 500mm")
    c1.drawString(250, 560, "12")
    c1.drawString(340, 560, "18.50")
    c1.drawRightString(550, 560, "222.00")
    
    c1.drawString(50, 545, "Corrugated boxes, large")
    c1.drawString(250, 545, "40")
    c1.drawString(340, 545, "2.35")
    c1.drawRightString(550, 545, "94.00")
    
    c1.drawString(50, 530, "Packing tape, brown")
    c1.drawString(250, 530, "24")
    c1.drawString(340, 530, "1.90")
    c1.drawRightString(550, 530, "45.60")
    
    # Summary amounts
    c1.drawRightString(550, 490, "Subtotal 361.60")
    c1.drawRightString(550, 470, "VAT 20% 72.32")
    c1.setFont("Helvetica-Bold", 11)
    c1.drawRightString(550, 450, "Amount Due GBP 433.92")
    c1.showPage()
    c1.save()

    with open(json_1, "w", encoding="utf-8") as f:
        json.dump({
            "vendor": "Northwind Traders",
            "invoice_number": "NW-1042",
            "invoice_date": "2026-09-03",
            "due_date": "2026-10-03",
            "currency": "GBP",
            "subtotal": 361.60,
            "tax": 72.32,
            "total": 433.92
        }, f, indent=2)

    # Example 2: Kestrel Components Inc. with terms Net 30 and US ambiguous date
    pdf_2 = output_dir / "appendix_n_example_2.pdf"
    json_2 = output_dir / "appendix_n_example_2.json"
    
    c2 = canvas.Canvas(str(pdf_2), pagesize=letter)
    c2.setFont("Helvetica-Bold", 11)
    c2.drawString(50, 750, "Kestrel Components Inc. | 880 Industrial Pkwy, Dayton OH 45402, USA")
    c2.setFont("Helvetica", 9)
    c2.drawString(50, 725, "Reference # KC-0311 Dated 9/3/26")
    c2.drawString(50, 710, "Terms Net 30")
    c2.drawString(50, 680, "Sold to Bruviti Services Pvt Ltd")
    
    # Line items table
    c2.drawString(50, 640, "Particulars")
    c2.drawRightString(550, 640, "Total")
    
    c2.drawString(50, 620, "Bearing kit 6204-2RS (x10)")
    c2.drawRightString(550, 620, "145.00")
    
    c2.drawString(50, 605, "Drive belt A-42 (x4)")
    c2.drawRightString(550, 605, "62.80")
    
    c2.drawString(50, 590, "Shipping")
    c2.drawRightString(550, 590, "18.00")
    
    c2.drawString(50, 570, "------------------------")
    
    # Summary amounts
    c2.drawRightString(550, 545, "Sub total 225.80")
    c2.drawRightString(550, 525, "Sales tax 7.25% 16.37")
    c2.setFont("Helvetica-Bold", 11)
    c2.drawRightString(550, 500, "Balance Due $ 242.17")
    c2.showPage()
    c2.save()

    with open(json_2, "w", encoding="utf-8") as f:
        json.dump({
            "vendor": "Kestrel Components",
            "invoice_number": "KC-0311",
            "invoice_date": "2026-09-03",
            "due_date": "2026-10-03",
            "currency": "USD",
            "subtotal": 225.80,
            "tax": 16.37,
            "total": 242.17
        }, f, indent=2)

    # Example 3: Unknown Vendor with no due date and no payment terms
    pdf_3 = output_dir / "unknown_vendor.pdf"
    json_3 = output_dir / "unknown_vendor.json"
    
    c3 = canvas.Canvas(str(pdf_3), pagesize=letter)
    c3.setFont("Helvetica-Bold", 14)
    c3.drawString(50, 750, "Apex Industrial Supplies Pvt Ltd")
    c3.setFont("Helvetica", 9)
    c3.drawString(50, 735, "Plot 42, MIDC, Andheri East, Mumbai, India")
    c3.drawString(50, 720, "GSTIN 27AAAAA0000A1Z5")
    
    c3.setFont("Helvetica-Bold", 16)
    c3.drawRightString(550, 750, "TAX INVOICE")
    
    c3.setFont("Helvetica", 9)
    c3.drawString(50, 680, "Bill To: Bruviti Services Pvt Ltd, Tech Park, Pune")
    
    c3.drawString(50, 640, "Invoice No: 7781")
    c3.drawString(50, 625, "Invoice Date: 21/08/2026")
    
    c3.drawRightString(550, 520, "Subtotal: INR 12,000.00")
    c3.drawRightString(550, 500, "GST 18%: INR 2,160.00")
    c3.setFont("Helvetica-Bold", 11)
    c3.drawRightString(550, 480, "Total: INR 14,160.00")
    c3.showPage()
    c3.save()

    ex3_data = {
        "vendor": "unknown",
        "invoice_number": "7781",
        "invoice_date": "2026-08-21",
        "due_date": None,
        "currency": "INR",
        "subtotal": 12000.0,
        "tax": 2160.0,
        "total": 14160.0
    }
    with open(json_3, "w", encoding="utf-8") as f:
        json.dump(ex3_data, f, indent=2)

    # Save prompt-named files: northwind_1042, kestrel_0311
    import shutil
    shutil.copyfile(pdf_1, output_dir / "northwind_1042.pdf")
    shutil.copyfile(json_1, output_dir / "northwind_1042.json")
    shutil.copyfile(pdf_2, output_dir / "kestrel_0311.pdf")
    shutil.copyfile(json_2, output_dir / "kestrel_0311.json")
    shutil.copyfile(pdf_3, output_dir / "appendix_n_example_3.pdf")
    shutil.copyfile(json_3, output_dir / "appendix_n_example_3.json")

def main():
    print("Generating invoice datasets...")
    
    # 1. Appendix N Golden Invoices
    app_n_dir = PROJECT_ROOT / "data" / "appendix_n"
    generate_appendix_n_invoices(app_n_dir)
    print("Generated Appendix N reference invoices (northwind_1042, kestrel_0311, unknown_vendor).")

    # 2. Synthetic Training/Dev Dataset (150 invoices)
    synth_dir = PROJECT_ROOT / "data" / "synthetic"
    synth_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, 151):
        generate_invoice_sample(i, synth_dir, is_holdout=False)
    print(f"Generated 150 synthetic invoices in {synth_dir}")

    # 3. Held-out Dataset (35 invoices)
    holdout_dir = PROJECT_ROOT / "data" / "handmade"
    holdout_dir.mkdir(parents=True, exist_ok=True)
    for i in range(151, 186):
        generate_invoice_sample(i, holdout_dir, is_holdout=True)
    print(f"Generated 35 held-out invoices in {holdout_dir}")

    print("Data generation complete!")

if __name__ == "__main__":
    main()
