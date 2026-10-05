from pathlib import Path

import pytest
import yaml

from pipeline.load import build_database

HERE = Path(__file__).parent


@pytest.fixture(scope="session")
def store(tmp_path_factory):
    """Fresh database built from the curated lane, isolated from db/."""
    tmp = tmp_path_factory.mktemp("kg")
    s = build_database(tmp / "cpg.kuzu", tmp / "parquet")
    yield s
    s.close()


@pytest.fixture(scope="session")
def expected():
    return yaml.safe_load((HERE / "expected.yaml").read_text(encoding="utf-8"))

