"""CQ4: How does Stage 5 differ between food & beverage and home care?"""
from collections import defaultdict

from retrieve.competency import cq4


def test_stage5_differs_between_food_and_home_care(store, expected):
    result = cq4(store, 5)
    by_sub = defaultdict(dict)
    for r in result["rows"]:
        by_sub[r["subsector"]][(r["element"], r["aspect"])] = r["variation"]
    fb, hc = by_sub["Food & beverage"], by_sub["Home care"]
    assert fb and hc, "both sub-sectors need Stage 5 variations"
    shared = set(fb) & set(hc)
    assert {aspect for _, aspect in shared} == set(expected["cq4"]["shared_aspects"])
    # the comparison is meaningful: same aspect, different practice
    assert all(fb[k] != hc[k] for k in shared)
    # personal care is excluded when not requested
    assert "Personal care" not in by_sub
