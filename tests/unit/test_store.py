import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from codegen.loader import ROOT
from graph.store import get_store


@pytest.fixture
def store(tmp_path):
    s = get_store().connect(tmp_path / "t.db")
    yield s
    s.close()


def test_multi_pair_rel_and_parquet_copy(store, tmp_path):
    store.apply_ddl(
        "CREATE NODE TABLE A(id STRING, tags STRING[], PRIMARY KEY(id));"
        "CREATE NODE TABLE B(id STRING, PRIMARY KEY(id));"
        "CREATE REL TABLE LINK_AB(FROM A TO B, FROM B TO A, note STRING);"
    )
    pq.write_table(pa.table({"id": ["a1"], "tags": [["x"]]}), tmp_path / "a.parquet")
    pq.write_table(pa.table({"id": ["b1"]}), tmp_path / "b.parquet")
    pq.write_table(pa.table({"from": ["a1"], "to": ["b1"], "note": ["n"]}), tmp_path / "ab.parquet")
    store.bulk_load_parquet("A", tmp_path / "a.parquet")
    store.bulk_load_parquet("B", tmp_path / "b.parquet")
    store.bulk_load_parquet("LINK_AB", tmp_path / "ab.parquet", "A", "B")
    rows = store.query("MATCH (a:A)-[e:LINK_AB]->(b:B) RETURN a.id AS a, b.id AS b, e.note AS n, a.tags AS t")
    assert rows == [{"a": "a1", "b": "b1", "n": "n", "t": ["x"]}]


def test_generated_ddl_applies(store):
    n = store.apply_ddl(ROOT / "gen" / "ddl" / "schema.cypher")
    tables = store.query("CALL show_tables() RETURN name")
    assert len(tables) == n


def test_query_params(store):
    store.apply_ddl("CREATE NODE TABLE A(id STRING, PRIMARY KEY(id));")
    store.query("CREATE (:A {id: $id})", {"id": "x"})
    assert store.query("MATCH (a:A {id: $id}) RETURN a.id AS id", {"id": "x"}) == [{"id": "x"}]
