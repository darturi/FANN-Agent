"""Read-only restored-data and physical-index verification, inherited from the A/B study."""
import json
from pathlib import Path
from design import digest


def verify_import(frozen, bundle, work):
    """Stream every ID, vote and float32 vector bit; avoid buffering the full table."""
    import numpy as np
    import psycopg
    from psycopg.conninfo import make_conninfo
    import pyarrow.parquet as parquet
    def expected_rows():
        for batch in parquet.ParquetFile(bundle/'inputs/reviews.parquet').iter_batches(batch_size=512):
            yield from batch.to_pylist()
    expected = expected_rows()
    count = 0
    with psycopg.connect(make_conninfo(frozen.job_connection(work, admin=True), dbname='torch_reviews')) as conn:
        with conn.cursor(name='verify_preserved_bits') as cursor:
            cursor.execute('SELECT id,embedding::text,total_votes FROM reviews ORDER BY id')
            for identifier, text, votes in cursor:
                row = next(expected, None)
                if row is None or identifier != row['source_id'] or votes != row['metadata']['total_votes']:
                    raise RuntimeError('Restored ID/metadata differs')
                if not np.array_equal(np.asarray(json.loads(text), dtype=np.float32).view(np.uint32),
                                      np.asarray(row['vector'], dtype=np.float32).view(np.uint32)):
                    raise RuntimeError('Restored vector bits differ')
                count += 1
    if next(expected, None) is not None or count != frozen.read(bundle/'experiment.json')['row_count']:
        raise RuntimeError('Restored row coverage differs')


def verify_index(work, expected):
    directory = (work/'pgdata'/expected['index_filepath']).parent
    actual = {p.name: digest(p) for p in directory.glob(Path(expected['index_filepath']).name+'*') if p.is_file()}
    if actual != expected['index_files']:
        raise RuntimeError('Physical HNSW index differs')
