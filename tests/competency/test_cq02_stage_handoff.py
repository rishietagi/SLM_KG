"""CQ2: What outputs of Stage 3 become inputs to Stage 4?"""
from retrieve.competency import cq2


def test_stage3_outputs_feed_stage4(store, expected):
    result = cq2(store, 3, 4)
    got = {(r["output"], r["consumer"]) for r in result["rows"]}
    assert got == {tuple(p) for p in expected["cq2"]["pairs"]}
    # every hand-off is a connected PRODUCES -> BECOMES_INPUT_TO path
    assert len(result["path"]) == 2 * len(result["rows"])
