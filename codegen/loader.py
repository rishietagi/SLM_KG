"""Load and merge all ontology/*.yaml files into one Ontology object."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from codegen.meta import Attribute, ClassDef, CommonFile, ModuleFile, Pair, RelDef, RelMapFile

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_DIR = ROOT / "ontology"
SPECIAL = {"common.yaml", "rel_name_map.yaml"}
# Spine first, so its relationship descriptions win when a name is reused by later modules.
PRIORITY = ["layer1_value_chain.yaml", "hooks.yaml"]


class OntologyError(Exception):
    pass


@dataclass
class Ontology:
    common: CommonFile
    classes: dict[str, ClassDef] = field(default_factory=dict)
    relationships: dict[str, RelDef] = field(default_factory=dict)
    rel_map: RelMapFile | None = None
    modules: list[str] = field(default_factory=list)
    hash: str = ""

    def node_attributes(self, cls: str) -> dict[str, Attribute]:
        """Common node attributes followed by class-specific ones."""
        return {**self.common.node_base, **self.classes[cls].attributes}

    def edge_properties(self, rel: str) -> dict[str, Attribute]:
        return {**self.common.edge_base, **self.relationships[rel].properties}

    def pair_set(self) -> set[tuple[str, str, str]]:
        return {(r, p.from_, p.to) for r, d in self.relationships.items() for p in d.pairs}


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _module_order(path: Path) -> tuple[int, str]:
    rank = PRIORITY.index(path.name) if path.name in PRIORITY else len(PRIORITY)
    return rank, path.name


def ontology_hash(directory: Path = ONTOLOGY_DIR) -> str:
    h = hashlib.sha256()
    for p in sorted(directory.glob("*.yaml")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def load_ontology(directory: Path = ONTOLOGY_DIR) -> Ontology:
    common = CommonFile.model_validate(_read(directory / "common.yaml"))
    onto = Ontology(common=common, hash=ontology_hash(directory))
    map_path = directory / "rel_name_map.yaml"
    if map_path.exists():
        onto.rel_map = RelMapFile.model_validate(_read(map_path))

    for path in sorted(directory.glob("*.yaml"), key=_module_order):
        if path.name in SPECIAL:
            continue
        mod = ModuleFile.model_validate(_read(path))
        onto.modules.append(mod.module)
        for name, cls in mod.classes.items():
            if name in onto.classes:
                raise OntologyError(
                    f"class {name} declared in both {onto.classes[name].module} and {mod.module}"
                )
            cls.module = mod.module
            onto.classes[name] = cls
        for name, rel in mod.relationships.items():
            _merge_rel(onto, name, rel, mod.module)
    return onto


def _merge_rel(onto: Ontology, name: str, rel: RelDef, module: str) -> None:
    for p in rel.pairs:
        p.hook_layer = p.hook_layer or rel.hook_layer
    existing = onto.relationships.get(name)
    if existing is None:
        rel.modules = [module]
        onto.relationships[name] = rel
        return
    for prop, attr in rel.properties.items():
        if prop in existing.properties and existing.properties[prop] != attr:
            raise OntologyError(f"{name}.{prop} declared with different types in {module}")
        existing.properties.setdefault(prop, attr)
    seen = {(p.from_, p.to) for p in existing.pairs}
    for p in rel.pairs:
        if (p.from_, p.to) in seen:
            raise OntologyError(f"{name} pair {p.from_}->{p.to} declared twice (again in {module})")
        existing.pairs.append(Pair.model_validate(p.model_dump(by_alias=True)))
        seen.add((p.from_, p.to))
    if existing.hook_layer is None:
        existing.hook_layer = rel.hook_layer
    existing.modules.append(module)
