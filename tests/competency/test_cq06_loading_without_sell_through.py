"""CQ6: Which trade promotions loaded distributors but did not produce outlet sell-through?"""
from retrieve.competency import cq6


def test_planted_loading_promotion_is_found(full_store, expected, truth):
    e = expected["cq6"]
    result = cq6(full_store, e["min_primary_uplift"], e["max_sell_out_uplift"])
    assert result["flagged"] == [f"TradePromotion:{p}" for p in truth["loaded_no_sell_through"]]
    # the healthy promotion is evaluated and not flagged
    healthy = {r["promotion_id"]: r for r in result["rows"]}[f"TradePromotion:{truth['healthy_promotions'][0]}"]
    assert healthy["primary_uplift"] >= e["min_primary_uplift"] and healthy["sell_out_uplift"] > e["max_sell_out_uplift"]
    # answer path reaches the loaded distributors through their customer accounts
    assert any(rel == "ACCOUNT_OF" for _, rel, _ in result["path"])
