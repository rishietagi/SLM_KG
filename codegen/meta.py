"""Meta-model for ontology YAML files. These Pydantic models *are* the ontology file schema."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AttrType = Literal[
    "string", "int64", "double", "decimal", "bool", "date", "timestamp", "string_list", "enum"
]

PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")
UPPER_SNAKE = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")
SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Attribute(_Strict):
    type: AttrType
    required: bool = False
    values: list[str] | None = None  # enum only
    description: str | None = None

    @model_validator(mode="after")
    def _enum_values(self) -> "Attribute":
        if self.type == "enum" and not self.values:
            raise ValueError("enum attribute needs `values`")
        if self.type != "enum" and self.values:
            raise ValueError("`values` only allowed for enum attributes")
        return self


class ClassDef(_Strict):
    layer: int = Field(ge=1, le=6)
    description: str
    source_key: str | None = None  # key name in the originating spec; DB PK is always `id`
    spec_ref: str | None = None
    stub: bool = False  # declared early as a hook target; attributes come in a later phase
    attributes: dict[str, Attribute] = {}
    module: str | None = None  # filled by the loader


class Pair(_Strict):
    from_: str = Field(alias="from")
    to: str
    cardinality: str | None = None
    note: str | None = None
    hook_layer: int | None = Field(default=None, ge=1, le=6)  # filled by the loader from the declaring RelDef


class RelDef(_Strict):
    description: str
    # Set on cross-layer hooks. Applies only to the pairs declared alongside it, not to pairs that
    # other modules add under the same name (e.g. finance's Risk AFFECTS FinancialAccount).
    hook_layer: int | None = Field(default=None, ge=1, le=6)
    pairs: list[Pair]
    properties: dict[str, Attribute] = {}
    modules: list[str] = []  # filled by the loader


class ModuleFile(_Strict):
    module: str
    description: str | None = None
    classes: dict[str, ClassDef] = {}
    relationships: dict[str, RelDef] = {}


class CommonFile(_Strict):
    module: Literal["common"]
    description: str | None = None
    type_map: dict[str, str]  # AttrType -> DDL type
    node_base: dict[str, Attribute]
    edge_base: dict[str, Attribute]
    forbidden_relationships: list[str] = []
    do_not_merge: list[list[str]] = []


class Slice(_Strict):
    description: str
    route_keywords: list[str]
    classes: list[str]
    relationships: list[str]


class SliceFile(_Strict):
    module: Literal["slices"]
    description: str | None = None
    slices: dict[str, Slice]


class RelMapEntry(_Strict):
    original: str
    from_: str = Field(alias="from")
    to: str
    canonical: str | None  # null when dropped/deferred
    canonical_from: str | None = None  # set when the subject class was mapped
    canonical_to: str | None = None  # set when the object class was mapped
    action: Literal["converted", "renamed", "retargeted", "mapped", "deferred", "dropped"]
    note: str | None = None


class RelMapFile(_Strict):
    module: Literal["rel_name_map"]
    description: str | None = None
    added: list[dict] = []  # pairs added beyond the finance spec (e.g. §6.1 fixes)
    entries: list[RelMapEntry]
