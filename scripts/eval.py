import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.pdf_text import extract_pdf_document
from app.fields import extract_invoice_fields

FIELDS = [
    "vendor",
    "invoice_number",
    "invoice_date",
    "due_date",
    "currency",
    "subtotal",
    "tax",
    "total"
]

def evaluate_directory(data_dir: Path) -> Dict[str, Any]:
    pdf_files = sorted(list(data_dir.glob("*.pdf")))
    if not pdf_files:
        print(f"No PDF files found in {data_dir}")
        return {}

    total_files = 0
    correct_counts = {f: 0 for f in FIELDS}
    errors = []

    for pdf_path in pdf_files:
        json_path = pdf_path.with_suffix(".json")
        if not json_path.exists():
            continue

        total_files += 1
        with open(json_path, "r", encoding="utf-8") as f:
            ground_truth = json.load(f)

        pdf_bytes = pdf_path.read_bytes()
        doc_info = extract_pdf_document(pdf_bytes)
        pred = extract_invoice_fields(doc_info).model_dump()

        file_errors = {}
        for f in FIELDS:
            gt_val = ground_truth.get(f)
            pred_val = pred.get(f)

            # Float comparison tolerance 0.01
            match = False
            if isinstance(gt_val, (int, float)) and isinstance(pred_val, (int, float)):
                match = abs(float(gt_val) - float(pred_val)) <= 0.01
            elif gt_val is None and pred_val is None:
                match = True
            elif str(gt_val).strip().lower() == str(pred_val).strip().lower():
                match = True

            if match:
                correct_counts[f] += 1
            else:
                file_errors[f] = {"expected": gt_val, "got": pred_val}

        if file_errors:
            errors.append({"file": pdf_path.name, "mismatches": file_errors})

    accuracies = {f: (correct_counts[f] / total_files) * 100.0 for f in FIELDS}
    overall_accuracy = sum(accuracies.values()) / len(FIELDS)

    return {
        "total_files": total_files,
        "correct_counts": correct_counts,
        "accuracies": accuracies,
        "overall_accuracy": overall_accuracy,
        "errors": errors
    }

def print_report(title: str, results: Dict[str, Any]):
    print("\n" + "=" * 65)
    print(f" {title.upper()} - EVALUATION REPORT ({results['total_files']} files)")
    print("=" * 65)
    print(f"{'Field':<18} | {'Correct':<10} | {'Total':<10} | {'Accuracy':<10}")
    print("-" * 65)
    for f in FIELDS:
        corr = results["correct_counts"][f]
        tot = results["total_files"]
        acc = results["accuracies"][f]
        print(f"{f:<18} | {corr:<10} | {tot:<10} | {acc:>7.2f}%")
    print("-" * 65)
    print(f"{'OVERALL AVERAGE':<18} | {'-':<10} | {'-':<10} | {results['overall_accuracy']:>7.2f}%")
    print("=" * 65)

    if results["errors"]:
        print(f"\nMismatches ({len(results['errors'])} files with discrepancies):")
        for err in results["errors"][:10]:
            print(f"  [{err['file']}]:")
            for fld, diff in err["mismatches"].items():
                print(f"    - {fld}: expected '{diff['expected']}', got '{diff['got']}'")
        if len(results["errors"]) > 10:
            print(f"  ... and {len(results['errors']) - 10} more files.")

def main():
    parser = argparse.ArgumentParser(description="Evaluate invoice field extraction")
    parser.add_argument("--holdout", action="store_true", help="Evaluate on held-out set")
    parser.add_argument("--appendix", action="store_true", help="Evaluate on Appendix N golden set")
    parser.add_argument("--all", action="store_true", help="Evaluate all datasets")
    args = parser.parse_args()

    if args.appendix:
        results = evaluate_directory(PROJECT_ROOT / "data" / "appendix_n")
        print_report("Appendix N Golden Reference", results)
    elif args.holdout:
        results = evaluate_directory(PROJECT_ROOT / "data" / "handmade")
        print_report("Held-Out Validation Set", results)
    elif args.all:
        print_report("Appendix N Golden Reference", evaluate_directory(PROJECT_ROOT / "data" / "appendix_n"))
        print_report("Synthetic Dev Set", evaluate_directory(PROJECT_ROOT / "data" / "synthetic"))
        print_report("Held-Out Validation Set", evaluate_directory(PROJECT_ROOT / "data" / "handmade"))
    else:
        results = evaluate_directory(PROJECT_ROOT / "data" / "synthetic")
        print_report("Synthetic Dev Set", results)

if __name__ == "__main__":
    main()
