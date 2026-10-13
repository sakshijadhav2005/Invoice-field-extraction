import os
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
    Creates the two golden reference invoices matching Example 1 and Example 2 from Appendix N.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Example 1: Harbour Engineering Ltd
    pdf_1 = output_dir / "appendix_n_example_1.pdf"
    json_1 = output_dir / "appendix_n_example_1.json"
    
    c1 = canvas.Canvas(str(pdf_1), pagesize=letter)
    c1.setFont("Helvetica-Bold", 14)
    c1.drawString(50, 750, "Harbour Engineering Ltd")
    c1.setFont("Helvetica", 9)
    c1.drawString(50, 735, "12 Temple Way, Bristol, UK")
    c1.drawString(50, 720, "VAT No GB123456789")
    
    c1.setFont("Helvetica-Bold", 16)
    c1.drawRightString(550, 750, "TAX INVOICE")
    
    c1.setFont("Helvetica", 9)
    c1.drawString(50, 680, "Bill To: Bruviti Services Pvt Ltd, Tech Park, Pune")
    
    c1.drawString(50, 640, "Invoice No: INV-2026-001")
    c1.drawString(50, 625, "Invoice Date: 03/09/2026")
    c1.drawString(50, 610, "Due Date: 03/10/2026")
    
    c1.drawRightString(550, 520, "Subtotal: £1,200.00")
    c1.drawRightString(550, 500, "VAT 20%: £240.00")
    c1.setFont("Helvetica-Bold", 11)
    c1.drawRightString(550, 480, "Total Due: £1,440.00")
    c1.showPage()
    c1.save()

    with open(json_1, "w", encoding="utf-8") as f:
        json.dump({
            "vendor": "Harbour Engineering Ltd",
            "invoice_number": "INV-2026-001",
            "invoice_date": "2026-09-03",
            "due_date": "2026-10-03",
            "currency": "GBP",
            "subtotal": 1200.00,
            "tax": 240.00,
            "total": 1440.00
        }, f, indent=2)

    # Example 2: Kestrel Components Inc. with terms Net 30 and US ambiguous date
    pdf_2 = output_dir / "appendix_n_example_2.pdf"
    json_2 = output_dir / "appendix_n_example_2.json"
    
    c2 = canvas.Canvas(str(pdf_2), pagesize=letter)
    c2.setFont("Helvetica-Bold", 14)
    c2.drawString(50, 750, "Kestrel Components Inc.")
    c2.setFont("Helvetica", 9)
    c2.drawString(50, 735, "Dayton, Ohio, USA")
    c2.drawString(50, 720, "EIN 31-1234567")
    
    c2.setFont("Helvetica-Bold", 16)
    c2.drawRightString(550, 750, "INVOICE")
    
    c2.setFont("Helvetica", 9)
    c2.drawString(50, 680, "Bill To: Bruviti Services Pvt Ltd")
    
    c2.drawString(50, 640, "Invoice Number: KC-8899")
    c2.drawString(50, 625, "Date: 9/3/26")
    c2.drawString(50, 610, "Terms: Net 30")
    
    c2.drawRightString(550, 520, "Subtotal: $2,500.00")
    c2.drawRightString(550, 500, "Sales Tax: $175.00")
    c2.setFont("Helvetica-Bold", 11)
    c2.drawRightString(550, 480, "Amount Due: $2,675.00")
    c2.showPage()
    c2.save()

    with open(json_2, "w", encoding="utf-8") as f:
        json.dump({
            "vendor": "Kestrel Components Inc.",
            "invoice_number": "KC-8899",
            "invoice_date": "2026-09-03",
            "due_date": "2026-10-03",
            "currency": "USD",
            "subtotal": 2500.00,
            "tax": 175.00,
            "total": 2675.00
        }, f, indent=2)

def main():
    print("Generating invoice datasets...")
    
    # 1. Appendix N Golden Invoices
    app_n_dir = PROJECT_ROOT / "data" / "appendix_n"
    generate_appendix_n_invoices(app_n_dir)
    print("Generated 2 Appendix N reference invoices.")

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
