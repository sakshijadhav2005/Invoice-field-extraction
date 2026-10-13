import pytest
from app.doctype import classify_document, DocTypeResult

def test_classify_standard_invoices():
    assert classify_document("TAX INVOICE\nInvoice #: 1001").doc_type == "invoice"
    assert classify_document("Rechnung Nr. 54321").doc_type == "invoice"
    assert classify_document("御請求書\n請求番号: 9876").doc_type == "invoice"
    assert classify_document("Commercial Invoice").doc_type == "invoice"

def test_classify_non_invoices():
    # Quotation
    res_quote = classify_document("QUOTATION\nQuote # 1001\nValid for 30 days")
    assert res_quote.doc_type == "quotation"
    assert not res_quote.is_invoice
    assert any("quotation" in w.lower() for w in res_quote.warnings)

    # Estimate
    res_est = classify_document("COST ESTIMATE\nEstimate # 55")
    assert res_est.doc_type == "quotation"
    assert not res_est.is_invoice

    # Delivery note / packing slip
    res_del = classify_document("DELIVERY NOTE / PACKING SLIP\nItems delivered")
    assert res_del.doc_type == "delivery_note"
    assert not res_del.is_invoice
    assert any("delivery note" in w.lower() for w in res_del.warnings)

    # Statement of account
    res_stmt = classify_document("STATEMENT OF ACCOUNT\nPeriod: Aug 2026")
    assert res_stmt.doc_type == "statement"
    assert not res_stmt.is_invoice

    # Credit note
    res_cn = classify_document("CREDIT NOTE\nCredit Memo # 404")
    assert res_cn.doc_type == "credit_note"
    assert not res_cn.is_invoice

    # Pro-forma invoice
    res_pro = classify_document("PRO FORMA INVOICE\nThis is not a tax invoice")
    assert res_pro.doc_type == "pro_forma"
    assert not res_pro.is_invoice
