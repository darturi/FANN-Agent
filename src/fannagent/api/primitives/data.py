from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldType(StrEnum):
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    STRING = "string"


class MetadataField(StrictModel):
    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    type: FieldType
    filterable: bool = True
    nullable: bool = False


class DatasetManifest(StrictModel):
    schema_version: Literal[1, 2] = 1
    name: str = Field(min_length=1)
    records_file: str = "records.parquet"
    row_count: int = Field(gt=0)
    dimension: int = Field(gt=0, le=65536)
    metric: Literal["cosine"] = "cosine"
    normalized: bool = True
    metadata_fields: list[MetadataField] = Field(default_factory=list)
    source: dict[str, Any] = Field(default_factory=dict)
    transformations: list[str] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)

    @model_serializer(mode="wrap")
    def versioned_serialization(self, handler: Any) -> dict[str, Any]:
        value = handler(self)
        if self.schema_version == 1:
            for field in value["metadata_fields"]:
                field.pop("nullable", None)
        return value

    @model_validator(mode="after")
    def unique_fields(self) -> DatasetManifest:
        if self.schema_version == 1 and any(field.nullable for field in self.metadata_fields):
            raise ValueError("nullable metadata requires dataset schema version 2")
        names = [field.name for field in self.metadata_fields]
        if len(names) != len(set(names)):
            raise ValueError("metadata field names must be unique")
        if {"id", "source_id", "vector"}.intersection(names):
            raise ValueError("metadata fields use a reserved name")
        return self


class VectorReference(StrictModel):
    file: str
    id: str


class Query(StrictModel):
    schema_version: Literal[1, 2] = 1
    id: str = Field(min_length=1)
    vector: list[float] | None = None
    vector_ref: VectorReference | None = None
    k: int = Field(gt=0, le=10_000)
    filter: dict[str, Any] | None = None

    @model_validator(mode="after")
    def one_vector_source(self) -> Query:
        if (self.vector is None) == (self.vector_ref is None):
            raise ValueError("exactly one of vector or vector_ref is required")
        return self


class LoadedDataset:
    def __init__(
        self,
        manifest_path: Path,
        manifest: DatasetManifest,
        ids: Any,
        source_ids: list[str],
        vectors: Any,
        metadata: dict[str, Any],
        dataset_hash: str,
        physical_fields: Any | None = None,
    ) -> None:
        self.manifest_path = manifest_path
        self.manifest = manifest
        self.ids = ids
        self.source_ids = source_ids
        self.vectors = vectors
        self.metadata = metadata
        self.dataset_hash = dataset_hash
        self.physical_fields = physical_fields

    def metadata_value(self, name: str, position: int) -> Any:
        import numpy as np

        value = self.metadata[name][position]
        if np.ma.is_masked(value):
            return None
        return value.item() if hasattr(value, "item") else value
