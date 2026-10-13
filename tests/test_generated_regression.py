import json
from pathlib import Path
from app.pdf_text import extract_pdf_document
from app.fields import extract_invoice_fields

def test_regression_synthetic_dataset_threshold():
    """
    Regression test ensuring that extraction accuracy across dev set remains above 95% on all fields.
    """
    synth_dir = Path(__file__).resolve().parent.parent / "data" / "synthetic"
    pdf_files = sorted(list(synth_dir.glob("*.pdf")))
    assert len(pdf_files) >= 50

    fields = ["vendor", "invoice_number", "invoice_date", "due_date", "currency", "subtotal", "tax", "total"]
    correct = {f: 0 for f in fields}
    total = 0

    for pdf_path in pdf_files:
        json_path = pdf_path.with_suffix(".json")
        if not json_path.exists():
            continue
        total += 1
        with open(json_path, "r", encoding="utf-8") as f:
            gt = json.load(f)

        pred = extract_invoice_fields(extract_pdf_document(pdf_path.read_bytes())).model_dump()

        for f in fields:
            gt_val = gt.get(f)
            pred_val = pred.get(f)
            if isinstance(gt_val, (int, float)) and isinstance(pred_val, (int, float)):
                match = abs(float(gt_val) - float(pred_val)) <= 0.01
            elif gt_val is None and pred_val is None:
                match = True
            elif str(gt_val).strip().lower() == str(pred_val).strip().lower():
                match = True
            else:
                match = False

            if match:
                correct[f] += 1

    for f in fields:
        acc = correct[f] / total
        assert acc >= 0.95, f"Field '{f}' accuracy dropped to {acc*100:.2f}% (must be >= 95%)"
