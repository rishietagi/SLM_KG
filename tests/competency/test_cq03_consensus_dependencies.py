"""CQ3: Which activities depend on the consensus demand forecast?"""
from retrieve.competency import cq3


def test_activities_depending_on_consensus_forecast(store, expected):
    e = expected["cq3"]
    result = cq3(store, e["term"])
    assert {r["activity"] for r in result["rows"]} == set(e["activities"])
    # dependencies cross stages: planning (6) feeds commercial (8)
    stages = {r["stage"] for r in result["rows"]}
    assert {"Demand, Supply and Inventory Planning", "Customer, Channel and Revenue Growth"} <= stages
