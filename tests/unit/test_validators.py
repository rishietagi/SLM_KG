"""Validators must catch violations, not just pass on good data."""
import copy

import pytest

from codegen.loader import load_ontology
from codegen.meta import ClassDef, Pair, RelDef
from pipeline.reference import ReferenceData
from validate.ontology_checks import check_ontology
from validate.orphans import find_orphans
from validate.reference_checks import check_reference


@pytest.fixture(scope="module")
def onto():
    return load_ontology()


def _mutated(onto):
    return copy.deepcopy(onto)


def test_real_ontology_is_clean(onto):
    assert check_ontology(onto) == []


def test_undeclared_class_detected(onto):
    o = _mutated(onto)
    o.relationships["PRECEDES"].pairs.append(Pair.model_validate({"from": "ValueChainStage", "to": "Ghost"}))
    assert any("undeclared class Ghost" in e for e in check_ontology(o))


def test_generic_relationship_forbidden(onto):
    o = _mutated(onto)
    o.relationships["RELATES_TO"] = RelDef(description="x", pairs=[Pair.model_validate({"from": "SKU", "to": "Brand"})])
    assert any("generic relationship forbidden" in e for e in check_ontology(o))


def test_category_belongs_to_brand_forbidden(onto):
    o = _mutated(onto)
    o.relationships["BELONGS_TO"].pairs.append(Pair.model_validate({"from": "Category", "to": "Brand"}))
    assert any("Category->Brand" in e for e in check_ontology(o))


def test_naming_conventions(onto):
    o = _mutated(onto)
    o.classes["bad_class"] = ClassDef(layer=1, description="x")
    o.relationships["badRel"] = RelDef(description="x", pairs=[Pair.model_validate({"from": "SKU", "to": "Brand"})])
    errors = check_ontology(o)
    assert any("not PascalCase" in e for e in errors)
    assert any("not UPPER_SNAKE_CASE" in e for e in errors)


def test_naming_drift(onto):
    o = _mutated(onto)
    o.classes["Sku"] = ClassDef(layer=3, description="dup")
    assert any("naming drift" in e for e in check_ontology(o))


def test_hook_layer_is_per_pair(onto):
    affects = {(p.from_, p.to): p.hook_layer for p in onto.relationships["AFFECTS"].pairs}
    assert affects[("Risk", "ValueChainActivity")] == 5
    assert affects[("Risk", "FinancialAccount")] is None  # finance pair, not a hook


def test_orphans():
    classes = {"CPGValueChain:r": "CPGValueChain", "A:1": "A", "A:2": "A", "A:3": "A"}
    assert find_orphans(classes, [("CPGValueChain:r", "A:1"), ("A:2", "A:1")]) == ["A:3"]


def _row(cls, node_id, **kw):
    base = dict(id=node_id, name=node_id, source_system="t", source_reference="docs/PROJECT_CONTEXT.md",
                extraction_confidence=1.0, lane="curated", reviewed=False, _class=cls, _file="t.yaml")
    return {**base, **kw}


def test_reference_rejects_disallowed_pair_and_missing_provenance(onto):
    data = ReferenceData()
    data.nodes["Input:x"] = _row("Input", "Input:x")
    data.nodes["SubSector:y"] = _row("SubSector", "SubSector:y", source_reference=None)
    data.edges.append(dict(relationship="CONSUMES", from_id="Input:x", to_id="SubSector:y",
                           from_type="Input", to_type="SubSector", source_system="t",
                           source_reference="docs/PROJECT_CONTEXT.md", extraction_confidence=1.0,
                           lane="curated", reviewed=False, _file="t.yaml"))
    errors = check_reference(onto, data)
    assert any("missing provenance field source_reference" in e for e in errors)
    assert any("CONSUMES not allowed from Input to SubSector" in e for e in errors)


def test_reference_rejects_bad_source_file_and_id_prefix(onto):
    data = ReferenceData()
    data.nodes["Output:z"] = _row("Input", "Output:z", source_reference="docs/source/missing.md#x")
    errors = check_reference(onto, data)
    assert any("missing file docs/source/missing.md" in e for e in errors)
    assert any("id prefix must be 'Input:'" in e for e in errors)
