from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError as ModelValidationError

from .api.primitives.contracts import MAX_FILTER_DEPTH
from .api.primitives.data import DatasetManifest, LoadedDataset, MetadataField, Query
from .api.primitives.errors import ValidationError
from .api.primitives.filters import validate_filter
from .api.profiles import DataProfile
from .errors import AgentError
from .store import digest
from .submission import InvalidSubmission


class Snapshot:
    def __init__(self, rows: list[dict], fields: list[dict], profile: DataProfile | None = None):
        self.profile = profile or DataProfile()
        if any(type(row["source_id"]) not in (int, str) for row in rows):
            raise AgentError("source identifiers must be integers or strings")
        if self.profile.identifier_representation == "int64" and any(
            type(row["source_id"]) is not int or not -(2**63) <= row["source_id"] < 2**63
            for row in rows
        ):
            raise AgentError("source identifiers must fit signed int64")
        if self.profile.identifier_representation == "string" and any(
            type(row["source_id"]) is not str for row in rows
        ):
            raise AgentError("source identifiers must be strings")
        rows = sorted(rows, key=lambda r: (type(r["source_id"]).__name__, r["source_id"]))
        self.source_ids = [row["source_id"] for row in rows]
        self._typed_source_to_id = {
            self.identifier_key(value): index for index, value in enumerate(self.source_ids)
        }
        source_ids = [str(r["source_id"]) for r in rows]
        if not rows or len(self._typed_source_to_id) != len(rows):
            raise AgentError("snapshot requires distinct identifiers and at least one row")
        self.source_to_id = (
            {value: index for index, value in enumerate(source_ids)}
            if len(set(source_ids)) == len(rows)
            else dict(self._typed_source_to_id)
        )
        self.id_to_source = source_ids
        self.field_map = {f"m_{i:06d}": f["name"] for i, f in enumerate(fields)}
        self.reverse_fields = {v: k for k, v in self.field_map.items()}
        self.fields = [
            {**field, "logical": logical} for logical, field in zip(self.field_map, fields)
        ]
        vectors = np.asarray([r["vector"] for r in rows], dtype=np.float32)
        if vectors.ndim != 2 or not np.isfinite(vectors).all():
            raise AgentError("vectors must be finite, rectangular float32 values")
        if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5, rtol=0):
            raise AgentError(
                "initial profile requires already normalized vectors; source unchanged"
            )
        if not self.profile.min_dimension <= vectors.shape[1] <= self.profile.max_dimension:
            raise AgentError("dimension is outside the selected data profile")
        manifest = DatasetManifest(
            schema_version=2,
            name="source_snapshot",
            row_count=len(rows),
            dimension=vectors.shape[1],
            metadata_fields=[
                MetadataField(name=f["logical"], type=f["type"], nullable=f.get("nullable", False))
                for f in self.fields
            ],
        )
        metadata = {}
        for field in self.fields:
            values = [r["metadata"].get(field["name"]) for r in rows]
            if field["type"] == "float" and any(
                v is not None and not np.isfinite(v) for v in values
            ):
                raise AgentError("floating-point metadata must be finite in this profile")
            metadata[field["logical"]] = np.ma.array(
                [
                    v
                    if v is not None
                    else {"integer": 0, "float": 0.0, "boolean": False, "string": ""}[field["type"]]
                    for v in values
                ],
                mask=[v is None for v in values],
            )
        identity = digest({"rows": rows, "fields": fields})
        self.data = LoadedDataset(
            Path("snapshot.json"),
            manifest,
            np.arange(len(rows), dtype=np.int64),
            source_ids,
            vectors,
            metadata,
            identity,
        )
        self.rows = rows
        self.identity = identity

    @staticmethod
    def identifier_key(value):
        return json.dumps([type(value).__name__, str(value)], separators=(",", ":"))

    def analysis_id(self, value):
        return self._typed_source_to_id[self.identifier_key(value)]

    def query(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            raise InvalidSubmission("invalid_query", "query must be a JSON object", path="query")

        def translate(node, depth=0):
            if depth > MAX_FILTER_DEPTH:
                raise InvalidSubmission(
                    "invalid_filter",
                    f"filter exceeds maximum depth {MAX_FILTER_DEPTH}",
                    path="filter",
                )
            if isinstance(node, dict):
                value = dict(node)
                if isinstance(value.get("field"), str):
                    value["field"] = self.reverse_fields.get(value["field"], value["field"])
                for op in ("and", "or"):
                    if isinstance(value.get(op), list):
                        value[op] = [translate(v, depth + 1) for v in value[op]]
                if "not" in value:
                    value["not"] = translate(value["not"], depth + 1)
                return value
            return node

        try:
            query = Query.model_validate(
                {"schema_version": 2, **raw, "filter": translate(raw.get("filter"))}
            )
        except ModelValidationError as exc:
            raise InvalidSubmission(
                "invalid_query",
                "query fields failed validation",
                details=[
                    {"path": "query." + ".".join(map(str, e["loc"])), "message": e["msg"]}
                    for e in exc.errors(
                        include_input=False, include_context=False, include_url=False
                    )
                ],
                hint="Supply id, an inline numeric vector, k, and an optional filter object.",
            ) from None
        with np.errstate(over="ignore", invalid="ignore"):
            vector = np.asarray(query.vector, dtype=np.float32)
        if vector.shape != (self.data.manifest.dimension,) or not np.isfinite(vector).all():
            raise InvalidSubmission(
                "invalid_query",
                "query dimension or numeric values are invalid",
                path="query.vector",
                hint=f"Supply exactly {self.data.manifest.dimension} finite float32 values.",
            )
        if not np.isclose(np.linalg.norm(vector), 1, atol=1e-5):
            raise InvalidSubmission(
                "invalid_query",
                "query vector must be normalized",
                path="query.vector",
                hint="Supply a vector with Euclidean norm 1; normalization is not automatic.",
            )
        if query.k > self.profile.max_k:
            raise InvalidSubmission(
                "invalid_query",
                "k is outside the selected data profile",
                path="query.k",
                hint=f"Use k between 1 and {self.profile.max_k}.",
            )
        try:
            validate_filter(query.filter, self.data.manifest)
        except ValidationError as exc:
            raise InvalidSubmission(
                "invalid_filter",
                str(exc),
                path="query." + exc.path,
                hint="Use declared fields and supported operators with matching value types.",
            ) from None

        def check(node):
            if not isinstance(node, dict):
                return
            if "field" in node:
                field = next(f for f in self.fields if f["logical"] == node["field"])
                if field.get("allowed_ops") and node["op"] not in field["allowed_ops"]:
                    raise InvalidSubmission(
                        "invalid_filter",
                        "predicate operator is outside the qualified field semantics",
                        path="query.filter",
                        hint="Use an operator listed in this field's allowed_ops.",
                    )
            for child in node.values():
                if isinstance(child, list):
                    for member in child:
                        check(member)
                elif isinstance(child, dict):
                    check(child)

        check(query.filter)
        return query.model_dump(mode="json", exclude_none=True)

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        vectors = pa.FixedSizeListArray.from_arrays(
            pa.array(self.data.vectors.reshape(-1), type=pa.float32()),
            self.data.manifest.dimension,
        )
        types = {
            "integer": pa.int64(),
            "float": pa.float64(),
            "boolean": pa.bool_(),
            "string": pa.string(),
        }
        columns = {
            "source_id": pa.array(self.source_ids)
            if len({type(v) for v in self.source_ids}) == 1
            else pa.array([self.identifier_key(v) for v in self.source_ids]),
            "vector": vectors,
        }
        if self.fields:
            columns["metadata"] = pa.array(
                [row["metadata"] for row in self.rows],
                type=pa.struct([pa.field(f["name"], types[f["type"]]) for f in self.fields]),
            )
        pq.write_table(pa.table(columns), path)

    def description(self) -> dict:
        return {
            "dataset_hash": self.identity,
            "row_count": len(self.rows),
            "dimension": self.data.manifest.dimension,
            "metric": "cosine",
            "fields": self.fields,
        }
