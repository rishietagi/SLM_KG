"""CQ6: Which KPIs measure outlet-execution outcomes, and which risk types affect those activities?"""
from retrieve.competency import cq6


def test_kpis_and_risks_for_outlet_execution(store, expected):
    e = expected["cq6"]
    r = cq6(store, e["stage"])
    assert r["kpis"] == sorted(e["kpis"])
    assert r["risks"] == sorted(e["risks"])
