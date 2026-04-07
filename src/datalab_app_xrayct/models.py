"""Pydantic models for the X-ray CT plugin.

The schema is intentionally split into ``acquisition`` (provenance from the
beamline) and ``reconstruction`` (geometry of the resulting volume) so that
either side can be missing or partially populated without breaking ingestion.

The :class:`RemoteAsset` model is the linchpin of the Control Plane / Data
Plane architecture: it carries a *URI*, never bytes. Phase 2's resolver will
translate the URI into a concrete mount path at job time.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class StorageScheme(str, Enum):
    DIAMOND = "diamond"  # diamond://<beamline>/<year>/<visit>/<rest>
    SCARF = "scarf"      # scarf://<project>/<rest>
    LOCAL = "file"       # file:///abs/path  (development only)
    S3 = "s3"            # s3://bucket/key


class RemoteAsset(BaseModel):
    """A pointer to a dataset on the Data Plane. Never carries raw bytes."""

    uri: str = Field(..., description="Universal URI; resolved in Phase 2.")
    scheme: StorageScheme
    size_bytes: int | None = None
    n_files: int | None = Field(
        None, description="Number of files for multi-file datasets (TIFF stacks)."
    )
    content_hash: str | None = Field(
        None,
        description="sha256 of a manifest of (path, size, mtime) entries — NOT a hash of the file bytes.",
    )
    last_seen: datetime | None = None

    @field_validator("uri")
    @classmethod
    def _scheme_present(cls, v: str) -> str:
        if "://" not in v:
            raise ValueError("URI must include a scheme, e.g. diamond://i13/2025/...")
        return v


class Vector3(BaseModel):
    z: float
    y: float
    x: float
    unit: str = "um"


class Shape3(BaseModel):
    z: int
    y: int
    x: int


class AcquisitionMetadata(BaseModel):
    """Beamline / instrument provenance."""

    facility: str | None = None
    beamline: str | None = None
    instrument: str | None = None
    technique: Literal["microCT", "nanoCT", "operando", "ptychography", "other"] = "microCT"
    beam_energy_kev: float | None = None
    exposure_time_s: float | None = None
    n_projections: int | None = None
    rotation_range_deg: float | None = None
    detector: str | None = None
    optics: str | None = None
    proposal_id: str | None = None
    visit_id: str | None = None
    sample_name: str | None = None
    acquired_at: datetime | None = None


class ReconstructionMetadata(BaseModel):
    voxel_size: Vector3 | None = None
    shape: Shape3 | None = None
    dtype: str | None = None
    algorithm: str | None = None
    software: str | None = None
    is_reconstructed: bool = False


class XrayCTMetadata(BaseModel):
    """Top-level metadata document persisted on the DataBlock."""

    schema_version: Literal["0.1"] = "0.1"
    title: str
    description: str | None = None

    asset: RemoteAsset
    acquisition: AcquisitionMetadata = Field(default_factory=AcquisitionMetadata)
    reconstruction: ReconstructionMetadata = Field(default_factory=ReconstructionMetadata)

    # Path (relative to datalab's FILE_DIRECTORY) of the central-slice preview PNG.
    # Stored as a path rather than base64 to keep block documents small in Mongo.
    preview_path: str | None = None
    preview_slice_index: int | None = None

    # Free-form bag for downstream phases (segmentation stats, tortuosity, ...).
    derived: dict = Field(default_factory=dict)
