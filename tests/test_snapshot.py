import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from fannagent.snapshot import Snapshot


@pytest.mark.parametrize("metadata", [True, False])
def test_sidecar_preserves_float32_and_extreme_bigint_keys(tmp_path, metadata):
    vector = np.asarray([1, 2, 3], dtype=np.float32)
    vector /= np.linalg.norm(vector)
    snapshot = Snapshot(
        [
            {"source_id": 2**63 - 1, "vector": vector.tolist(), "metadata": {"nullable": None}},
            {"source_id": -(2**63), "vector": vector.tolist(), "metadata": {"nullable": None}},
        ],
        [{"name": "nullable", "type": "integer", "nullable": True}] if metadata else [],
    )
    path = tmp_path / "sidecar.parquet"
    snapshot.save(path)
    table = pq.read_table(path)
    assert table["source_id"].to_pylist() == [-(2**63), 2**63 - 1]
    assert table["vector"].type.value_type == pa.float32()
    np.testing.assert_array_equal(
        np.asarray(table["vector"].to_pylist(), dtype=np.float32), snapshot.data.vectors
    )
    assert snapshot.id_to_source == [str(-(2**63)), str(2**63 - 1)]
