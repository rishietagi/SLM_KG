from pathlib import Path

import pytest
import yaml

from pipeline.load import build_database

HERE = Path(__file__).parent


@pytest.fixture(scope="session")
def store(tmp_path_factory):
    """Fresh database built from the curated lane, isolated from db/."""
    tmp = tmp_path_factory.mktemp("kg")
    s = build_database(tmp / "cpg.kuzu", tmp / "parquet", include_extracted=False)
    yield s
    s.close()


@pytest.fixture(scope="session")
def expected():
    return yaml.safe_load((HERE / "expected.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def full_store(tmp_path_factory):
    """Both lanes, built offline: synth (if absent) -> stage -> extract (replay) -> resolve -> fresh DB."""
    import os

    from codegen.loader import ROOT
    from extract.run import run as extract
    from pipeline.tabular import run as stage
    from resolve.resolver import run as resolve

    synth = ROOT / "data" / "synthetic"
    if not (synth / "truth.json").exists():
        import runpy

        runpy.run_path(str(synth / "generate.py"), run_name="__main__")
    os.environ["KG_LLM"] = "replay"
    stage()
    extract()  # missing fixtures only leave the document lane empty; CQ7 then skips
    resolve()
    tmp = tmp_path_factory.mktemp("kg_full")
    s = build_database(tmp / "cpg.kuzu", tmp / "parquet", include_extracted=True)
    yield s
    s.close()


@pytest.fixture(scope="session")
def truth():
    import json

    from codegen.loader import ROOT

    return json.loads((ROOT / "data" / "synthetic" / "truth.json").read_text(encoding="utf-8"))
