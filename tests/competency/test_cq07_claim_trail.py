"""CQ7: For promotion X, what was claimed, approved and settled, against which invoices and SKUs?"""
import pytest

from codegen.loader import ROOT
from retrieve.competency import cq7


def _fixtures_recorded() -> bool:
    d = ROOT / "tests" / "fixtures" / "llm"
    return d.exists() and any(d.glob("*.json"))


@pytest.mark.skipif(not _fixtures_recorded(), reason="no recorded LLM responses yet: run `KG_LLM=gemini make extract`")
def test_claim_trail_for_promotion(full_store, expected, truth):
    pid = expected["cq7"]["promotion"]
    result = cq7(full_store, f"TradePromotion:{pid}")
    got = {r["claim_id"].split(":", 1)[1]: r for r in result["rows"]}
    want = {cid: c for cid, c in truth["claims"].items() if c["promotion"] == pid}
    assert set(got) == set(want)
    for cid, c in want.items():
        r = got[cid]
        assert r["claimed"] == c["claimed"], cid
        assert (r["approved"] or 0) == c["approved"], cid
        assert r["customer_id"] == f"Customer:{c['customer']}", cid
        assert r["invoice_id"] == f"SalesInvoice:{c['invoice']}", cid
        assert r["sku_id"] == f"SKU:{c['sku']}", cid
        settled_by = r["credit_note_id"] or r["settlement_id"]
        assert (settled_by.split(":", 1)[1] if settled_by else "") == c["settlement"], cid
        if c["status"] == "rejected":
            assert r["status"] == "rejected", cid
    # provenance: every claim cites the document it came from
    assert all(r["source_reference"].startswith("data/synthetic/documents/") for r in result["rows"])
