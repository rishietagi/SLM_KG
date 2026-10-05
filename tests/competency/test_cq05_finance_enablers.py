"""CQ5: Which finance L3 processes enable outlet execution activities?"""
from retrieve.competency import cq5


def test_l3_processes_enabling_outlet_execution(full_store, expected):
    e = expected["cq5"]
    result = cq5(full_store, e["stage"])
    assert {r["endpoint"] for r in result["rows"]} == set(e["endpoints"])
    # every endpoint sits in a process group and a finance domain (no orphan process nodes)
    assert all(r["process_group"] and r["domain"] for r in result["rows"])
