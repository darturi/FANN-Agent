# FANNBench logical-to-physical field isolation implementation plan

Date: 2026-09-20  
Status: implemented and live-qualified on the local arm64 host  
Severity: high before real-data qualification  
Scope: canonical dataset validation, backend schema creation, ingestion, filter translation, conformance, provenance, tests, and documentation

Implementation evidence: FANNBench now uses the shared
`metadata_ordinal_v1` encoder and backend storage-schema version 2. The complete
non-integration suite passes with 91 tests and eight Docker tests deselected.
The five-test Docker smoke suite passes, including a combined live
instrumented run whose logical fields are `embedding`, `canonical_id`, `_id`,
and `year`. All three engines verified their stored physical schemas, matched
the oracle's eligible-ID sets, and returned valid measured vector responses.
The existing three-engine, four-mode instrumented route suite also passes. The
0.4.0 source distribution and wheel build successfully, and the wheel exposes
the new field-mapping module from a clean installation.

## 1. Goal

Make every valid logical metadata name behave the same in PostgreSQL/pgvector,
Elasticsearch, and Weaviate, even when that name has a special meaning in one
of those systems.

Dataset manifests and queries will continue to use readable logical names such
as `year`, `embedding`, `canonical_id`, or `_id`. The databases will never use
those names directly. FANNBench will translate them into short, safe internal
names before creating schemas, loading records, or rendering filters.

Example:

| Logical name in the dataset and query | Internal database name |
|---|---|
| `year` | `fb_meta_000000` |
| `embedding` | `fb_meta_000001` |
| `canonical_id` | `fb_meta_000002` |
| `_id` | `fb_meta_000003` |

The internal name is based on the field's position in the ordered manifest,
not on the logical text. This makes the mapping deterministic, one-to-one
within a dataset, short enough for every backend, and unable to collide with
backend-owned fields.

This change will also require `records.parquet` to contain exactly the three
canonical columns plus the metadata fields declared in the manifest. Extra
undeclared columns will be rejected rather than silently ignored.

## 2. Current problem

The canonical format already reserves `id`, `source_id`, and `vector`, but the
adapters currently reuse every other logical metadata name as a physical field
name.

That creates backend-specific collisions:

- pgvector owns the physical column `embedding`;
- Elasticsearch owns `vector` and `source_id`, while names such as `_id` have
  special meaning in its API;
- Weaviate owns the properties `canonical_id` and `source_id`; and
- future engine versions may introduce additional reserved names.

The same direct names are used during schema creation, record ingestion,
filtered vector search, complete eligible-ID queries, and diagnostics. Adding
only a longer reserved-word list would therefore remain fragile and would make
the portable contract depend on the current releases of all three databases.

The dataset loader also verifies required and declared columns but currently
ignores extra Parquet columns. That means the manifest is not a complete
description of the record schema.

## 3. Design decisions

### 3.1 Keep logical names stable

Do not rewrite manifests, query files, oracle metadata, or user-facing error
messages. These components continue to use the logical names supplied by the
dataset author.

Continue to reserve `id`, `source_id`, and `vector` as logical metadata names
because they are columns in the canonical Parquet format. Names that collide
only with backend internals, including `embedding`, `canonical_id`, and `_id`,
will become valid and safe through physical encoding.

### 3.2 Introduce one shared field map

Add `src/fannbench/field_names.py` with:

- `PHYSICAL_FIELD_ENCODING = "metadata_ordinal_v1"`;
- `BACKEND_STORAGE_SCHEMA_VERSION = 2`;
- a frozen `PhysicalFieldMap` value object;
- `PhysicalFieldMap.from_manifest(manifest)`;
- `physical_name(logical_name)` with a clear error for an unknown name; and
- a serializable list of logical/physical pairs for preparation provenance.

For the metadata field at zero-based manifest position `n`, use:

```text
fb_meta_<n padded to at least six decimal digits>
```

The width may expand if necessary, so the function remains one-to-one for any
accepted field count. Add an internal assertion that all generated names are
unique and match the conservative backend-safe pattern
`^[a-z][a-z0-9_]*$`.

Manifest order is already part of the canonical dataset hash. Therefore the
same dataset identity always produces the same mapping, while reordering
fields correctly produces a different dataset identity and mapping.

### 3.3 Keep backend-owned fields separate

The adapters may retain their current internal fields:

- pgvector: `id`, `source_id`, and `embedding`;
- Elasticsearch: document `_id`, `source_id`, and `vector`; and
- Weaviate: `canonical_id`, `source_id`, and the object vector.

Only metadata fields use the `fb_meta_...` namespace. Add constants for each
adapter's internal names so schema, ingestion, search, result extraction, and
eligible-ID code cannot drift through repeated string literals.

### 3.4 Reject undeclared record columns

In `load_dataset`, calculate:

```text
expected = {id, source_id, vector} union declared metadata fields
actual = records.parquet column names
```

Fail before any database starts when either set differs. The error must list
missing and unexpected columns separately. Column order remains irrelevant.

`write_canonical_dataset` already writes only the canonical and declared
columns, so generated datasets require no format change.

## 4. Implementation work

### Phase A: central mapping and dataset validation

Files:

- `src/fannbench/field_names.py` — new module
- `src/fannbench/data.py`
- `src/fannbench/models.py`
- `src/fannbench/contracts.py`, if the storage-schema version is kept with
  other shared contract constants

Actions:

1. Implement the deterministic `PhysicalFieldMap`.
2. Preserve the existing duplicate-name and canonical-column checks in
   `DatasetManifest`.
3. Add exact Parquet column-set validation immediately after the table is read.
4. Construct the field map during dataset loading as an early invariant check.
5. Add the map to `LoadedDataset`, or expose it as a deterministic property, so
   all adapters consume the same object rather than recreating local rules.
6. Keep `dataset.metadata` keyed by logical name. The oracle must remain
   completely independent of backend physical names.

Preferred model change:

```text
LoadedDataset.physical_fields: PhysicalFieldMap
```

If importing the mapping type into `models.py` would create a module cycle,
store it as an immutable `dict[str, str]` on `LoadedDataset` and keep creation
and validation in `field_names.py`.

### Phase B: filter translators

Files:

- `src/fannbench/adapters/sql_filters.py`
- `src/fannbench/adapters/elasticsearch.py`
- `src/fannbench/adapters/weaviate.py`

Actions:

1. Change `postgres_filter` to accept the logical-to-physical mapping.
2. Pass the mapping through every recursive `and`, `or`, and `not` branch.
3. Render each PostgreSQL leaf with
   `sql.Identifier(mapping.physical_name(expr["field"]))`.
4. Change `_elasticsearch_filter` to translate the leaf field before creating
   `term`, `terms`, or `range` JSON.
5. Change `_weaviate_filter` to use the logical name for type lookup and the
   physical name for its GraphQL `path`.
6. Convert any impossible missing-map lookup into a clear harness error naming
   the logical field. Do not allow a raw `KeyError` to escape.

Filter validation still happens against logical manifest names before
translation. Physical names must never appear in query JSON.

### Phase C: pgvector adapter

File:

- `src/fannbench/adapters/pgvector.py`

Actions:

1. Save the field map by `resource_name` when `prepare_dataset` begins. This
   must happen on both fresh creation and resource reuse.
2. Create metadata columns using their physical names.
3. Build the insert column list with physical names while reading values from
   `dataset.metadata` by logical name.
4. Name scalar indexes by field ordinal rather than logical name, for example
   `<resource>_meta_000000_idx`. This also avoids PostgreSQL's identifier-length
   problems for long logical names.
5. Pass the saved map into filtered vector search, instrumented search,
   eligible-ID queries, and diagnostic `EXPLAIN` queries.
6. Keep the canonical ID, source ID, and embedding columns unchanged.

### Phase D: Elasticsearch adapter

File:

- `src/fannbench/adapters/elasticsearch.py`

Actions:

1. Save the field map by `resource_name` during preparation, including reuse.
2. Create strict index mappings with physical metadata property names.
3. Write bulk documents with physical property names while reading logical
   metadata values.
4. Pass the field map into normal search, instrumented search, diagnostic
   profiling, and eligible-ID filter rendering.
5. Keep document `_id`, `source_id`, and `vector` as adapter-owned fields.
6. Verify that no logical metadata name is sent as a JSON property or query
   field.

### Phase E: Weaviate adapter

File:

- `src/fannbench/adapters/weaviate.py`

Actions:

1. Replace the current resource-to-field-type cache with resource-scoped
   logical field types plus the shared physical map.
2. Declare metadata properties under physical names.
3. Write batch object properties under physical names while reading logical
   metadata values.
4. Translate every filter path in regular search, instrumented search, and
   eligible-ID pagination.
5. Continue selecting only the adapter-owned `canonical_id` when returning
   result IDs.
6. Verify that logical metadata named `canonical_id` or `_id` cannot shadow
   adapter-owned values; `source_id` remains reserved by the canonical format.

### Phase F: resource reuse and provenance

Files:

- `src/fannbench/runner.py`
- `src/fannbench/runtime/registry.py`
- `src/fannbench/adapters/base.py`, if common cache helpers are introduced
- `src/fannbench/results.py`, only if preparation serialization needs support

Actions:

1. Include `BACKEND_STORAGE_SCHEMA_VERSION` and
   `PHYSICAL_FIELD_ENCODING` in the resource configuration hash used by
   `_get_or_create_resource`.
2. This must produce new resource identities so databases built with direct
   logical names are never reused after the change.
3. Add the encoding version, storage-schema version, and logical/physical map
   to each backend's `Preparation.details`.
4. Bump `preparation.json` from schema version 2 to version 3 because it gains a
   required field-mapping contract. The run, measurement, summary, and
   diagnostic schemas do not need to change.
5. On reuse, inspect enough backend schema information to confirm the expected
   physical fields exist. Row count alone must no longer be sufficient.
6. If schema inspection fails, rebuild the incomplete/incompatible resource and
   record that fact in preparation details.

No in-place database migration is required. Existing managed resources remain
available for explicit cleanup but are not eligible for reuse.

## 5. Test plan

### 5.1 Mapping unit tests

Add `tests/test_field_names.py` covering:

- deterministic output for the same manifest;
- unique physical names for every logical name;
- safe syntax and short names;
- adversarial logical names `embedding`, `canonical_id`, `_id`, `source`, and a
  long but valid identifier;
- a changed manifest order producing the corresponding changed ordinal map;
- an unknown logical lookup producing a clear error; and
- serialization of the mapping and encoding version.

### 5.2 Dataset validation tests

Extend `tests/test_data.py` to prove:

- exactly declared columns load successfully regardless of column order;
- an unexpected Parquet column is rejected and named in the error;
- multiple unexpected columns are reported deterministically;
- missing and unexpected columns are reported separately;
- `id`, `source_id`, and `vector` remain forbidden as metadata names; and
- backend-specific names such as `embedding`, `canonical_id`, and `_id` are
  accepted as logical metadata.

### 5.3 Translation tests

Update `tests/test_translations.py` so nested Boolean expressions are still
preserved, but every leaf uses the expected `fb_meta_...` physical name.

Add assertions that:

- no logical field appears in rendered PostgreSQL SQL;
- Elasticsearch `term`, `terms`, and `range` clauses use physical names;
- Weaviate uses physical paths but still selects the correct logical type for
  `valueInt`, `valueNumber`, `valueBoolean`, or `valueText`; and
- missing mapping entries fail explicitly.

### 5.4 Adapter and reuse tests

Add focused mocked-adapter tests where practical to inspect:

- created schemas and mappings;
- ingested property/column names;
- reuse schema validation;
- forced rebuild of an old direct-name schema; and
- preparation provenance.

Update runner and execution-observability fixtures that currently expect
`preparation.json` schema version 2.

### 5.5 Docker integration tests

Create a small adversarial fixture containing at least these logical fields:

```text
embedding, canonical_id, _id, year
```

Give each field distinct values and create filters that exercise equality,
membership, ranges, and nested Boolean logic.

For all three backends:

1. prepare the dataset;
2. inspect the stored schema and confirm the expected physical fields;
3. confirm that backend-colliding logical names are absent physically;
4. compare complete eligible-ID sets with the Python oracle;
5. run vector search and validate returned IDs and recall;
6. repeat with the existing ordinary fixture to catch regressions; and
7. run at least one instrumented mode to prove the same mapping works through
   the custom execution path.

The existing stock all-backend conformance test and the instrumented route
test must both remain green.

## 6. Documentation changes

Files:

- `docs/formats.md`
- `docs/methodology.md`
- `docs/compatibility.md`
- `README.md`

Document in simple terms that:

- manifests and queries always use logical names;
- FANNBench assigns backend-safe internal names automatically;
- users must never write `fb_meta_...` names in queries;
- only `id`, `source_id`, and `vector` are reserved in the canonical Parquet
  namespace;
- undeclared Parquet columns are errors; and
- physical mappings and their version are recorded in `preparation.json`.

Do not publish backend reserved-word lists as part of the user contract. The
encoding is specifically intended to make those lists irrelevant.

## 7. Validation sequence

Run the following gates in order:

1. formatting, linting, and the complete non-integration test suite;
2. focused mapping, data, translation, runner, and result tests;
3. clean construction and loading of both standard and adversarial fixtures;
4. stock Docker filter conformance across all three backends;
5. instrumented Docker route/conformance tests across all three backends;
6. resource-reuse test using the new schema version;
7. negative reuse test proving an old physical schema is rebuilt; and
8. a clean-package installation smoke test.

No engine patch rebuild should be necessary because the change is confined to
canonical validation and Python adapters. Rebuild engine images only if live
qualification shows that an instrumented engine has an undocumented dependency
on a metadata field name.

## 8. Acceptance criteria

The issue is closed only when all of the following are true:

1. A canonical dataset using logical fields `embedding`, `canonical_id`, and
   `_id` loads into all three databases without collision.
2. The same adversarial filters produce exactly the same eligible canonical IDs
   in the Python oracle and every backend.
3. Vector queries over that fixture pass normal correctness evaluation.
4. Every backend schema contains the expected physical metadata names and no
   direct logical metadata names.
5. Schema creation, ingestion, normal search, instrumented search, eligible-ID
   checks, and diagnostics all use the same map.
6. Extra undeclared Parquet columns fail before database startup with a clear
   error.
7. Old direct-name resources cannot be silently reused.
8. `preparation.json` records the mapping and its version for every backend.
9. Existing datasets and queries that obey the canonical schema continue to
   work without edits.
10. Unit, stock integration, instrumented integration, lint, whitespace, and
    clean-install gates pass.

## 9. Rollback and risk controls

- Keep this change in the harness and adapters; do not modify canonical source
  datasets in place.
- Do not reuse old resources, so rollback only requires running the older
  harness against its own resource identity.
- Use one central mapping implementation. Backend-specific mapping rules are
  prohibited because they would recreate the original portability risk.
- Never derive a physical field from unchecked query text. Only validated
  manifest fields may enter the mapping.
- Keep SQL values parameterized and SQL identifiers quoted even though physical
  names are generated by FANNBench.

## 10. Expected result

After implementation, database-reserved field names stop being a user-visible
compatibility concern. A dataset author uses one logical schema, every backend
receives a safe deterministic physical schema, and all translations are
recorded and testable. The change removes a high-severity portability gap
without changing the agent-policy interface or the meaning of existing query
files.
