"""Extraction lane building blocks: coercion, LLM-output conversion, routing, resolution."""
import pytest

from codegen.loader import load_ontology
from extract.chunk import Chunk
from extract.llm_client import ReplayClient, MissingFixture
from extract.route import route
from extract.run import coerce, to_records
from pipeline.staging import entity, rel, source
from resolve.resolver import resolve


@pytest.fixture(scope="module")
def onto():
    return load_ontology()


def test_coerce_amounts_keep_exact_text(onto):
    attrs, problems = coerce(onto.classes["PromotionClaim"].attributes, [
        {"key": "claim_amount", "value": "INR 620,000"}, {"key": "status", "value": "partially_approved"},
        {"key": "claim_date", "value": "14 August 2026"}, {"key": "colour", "value": "blue"}])
    assert attrs["claim_amount"] == 620000.0 and attrs["claim_amount_text"] == "INR 620,000"
    assert attrs["claim_date"] == "2026-08-14"
    assert problems == ["attribute 'colour' not in ontology (value 'blue')"]


class _Client:
    name = "test"


def test_disallowed_pair_goes_to_unresolved(onto):
    chunk = Chunk("data/synthetic/documents/x.md", 0, "x", "text")
    resp = {"entities": [{"entity_type": "PromotionClaim", "entity_id": "CLM1", "name": "CLM1", "attributes": [],
                          "confidence": 0.9},
                         {"entity_type": "SKU", "entity_id": "S1", "name": "S1", "attributes": [], "confidence": 0.9}],
            "relationships": [{"subject_type": "SKU", "subject_id": "S1", "relationship": "SETTLES",
                               "object_type": "PromotionClaim", "object_id": "CLM1", "confidence": 0.5}],
            "unresolved_items": []}
    recs = to_records(onto, chunk, resp, _Client())
    kinds = [r["kind"] for r in recs]
    assert kinds.count("entity") == 2 and kinds.count("relationship") == 0 and kinds.count("unresolved") == 1
    assert recs[0]["entity_id"] == "PromotionClaim:CLM1"
    assert recs[0]["source"]["source_reference"] == "data/synthetic/documents/x.md#x"


def test_routing(onto):
    claim = Chunk("f", 0, "s", "Distributor D107 submits claim CLM1 against promotion TP1; credit note follows.")
    circular = Chunk("f", 0, "s", "Trade circular. Mechanic: rebate. Offer period ... Eligible products ... Budget ...")
    assert route(claim, onto) == "claims_settlement"
    assert route(circular, onto) == "trade_promotion"


def test_replay_without_fixture_raises():
    with pytest.raises(MissingFixture):
        ReplayClient().extract("system-not-recorded", "user", {"type": "object"})


TAB = source("synthetic_mdm", "r1", "data/synthetic/tabular/x.csv#row=2")
LLM = source("llm_test", "doc#0", "data/synthetic/documents/doc.md#doc", 0.9)


def test_resolution_order_and_merge(onto):
    ents = [entity("Customer", "D107", "Baner Distribution", TAB, customer_type="distributor"),
            entity("Channel", "GT", "General trade", TAB, channel_type="traditional"),
            entity("Customer", "D107", "Distributor D107", LLM),                 # exact id
            entity("Channel", "general_trade", "General Trade", LLM),            # alias / master name
            entity("Customer", "baner_distributon", "Baner Distributon", LLM),   # fuzzy (typo)
            entity("Customer", "X999", "Unknown Traders", LLM),                  # master class, no match -> review
            entity("PromotionClaim", "CLM1", "CLM1", LLM, claim_amount=1.0, currency="INR", status="submitted"),
            entity("PromotionClaim", "CLM1", "CLM1", LLM, approved_amount=1.0, status="settled")]
    rels = [rel("PromotionClaim", "CLM1", "SUBMITTED_BY", "Customer", "D107", LLM),
            rel("PromotionClaim", "CLM1", "SUBMITTED_BY", "Customer", "X999", LLM)]
    res = resolve(ents, rels)
    assert set(res.entities) == {"Customer:D107", "Channel:GT", "PromotionClaim:CLM1"}
    assert res.stats["alias"] == 1 and res.stats["fuzzy"] == 1 and res.stats["review"] == 1
    d107 = res.entities["Customer:D107"]
    assert d107["name"] == "Baner Distribution" and "Distributor D107" in d107["aliases"]  # structured lane wins
    claim = res.entities["PromotionClaim:CLM1"]
    assert claim["attributes"]["status"] == "settled" and claim["attributes"]["approved_amount"] == 1.0
    assert len(res.review) == 2  # the unknown customer and the edge pointing at it


def test_core_constraint_rejects_claim_without_promotion(onto):
    ents = [entity("Customer", "D1", "D1", TAB, customer_type="distributor"),
            entity("PromotionClaim", "CLM2", "CLM2", LLM, claim_amount=5.0, currency="INR", status="submitted")]
    rels = [rel("PromotionClaim", "CLM2", "SUBMITTED_BY", "Customer", "D1", LLM)]
    res = resolve(ents, rels, onto)
    assert "PromotionClaim:CLM2" not in res.entities
    assert any("CLAIMED_AGAINST" in r for r in res.rejected[0]["reasons"])
