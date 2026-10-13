# AI.md: AI Assistance Attribution

This document describes how AI assistance was utilized in the development of the Invoice Field Extraction system, in compliance with academic and corporate integrity guidelines.

---

## 1. Scope of AI Usage

AI tooling (Antigravity AI Assistant powered by Gemini) was utilized for the following tasks:

1. **Multilingual Lexicon Brainstorming:**
   - Generating label vocabularies across English, German (`Rechnung`, `MwSt`, `Nettobetrag`, `Fällig am`), Japanese (`請求書番号`, `請求日`, `支払期限`, `消費税`, `小計`), and Indian billing standards (`GSTIN`, `Bill No`).
2. **Synthetic Generator Design:**
   - Designing independent variation axes for ReportLab generation (layouts, font noise, date conventions, term representations, arithmetic discrepancies).
3. **Adversarial Test Scenario Ideation:**
   - Formulating edge cases for test coverage, including:
     - Day/month collisions ($DD \le 12$ and $MM \le 12$)
     - Line items table headers containing "Total" column conflicting with summary totals
     - Company registration tax IDs (`VAT No GB123456789`) conflicting with VAT amount lines
     - Payment terms conflicting with printed due dates
     - Font glyph substitutions (e.g. `₹` mapped to ASCII artifacts).

---

## 2. Verification and Code Ownership

- **100% Deterministic Codebase:** All code implemented in the repository consists of standard, inspectable Python modules without black-box or non-deterministic calls.
- **Full Test Coverage:** 54 automated pytest tests verify all normalizers, business rules (O1–O5), edge cases, and API contracts.
- **Independent Validation:** All extraction logic was tested on both synthetic development and held-out test datasets, verifying that the rules generalize beyond training examples.
