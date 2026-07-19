from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

LicenseStatus = Literal["accepted", "rejected", "review_required", "missing"]
ValidationStatus = Literal["valid", "invalid", "missing", "review_required"]

class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["rebrickable_csv", "rebrickable_api", "manual_verified"]
    source_record_id: str | None = None
    retrieved_at: datetime
    source_version: str | None = None
    source_sha256: str | None = None

class LDrawRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str | None = None
    file_sha256: str | None = None
    header_name: str | None = None
    license_raw: str | None = None
    license_status: LicenseStatus
    attribution_required: bool
    validation_status: ValidationStatus

class Geometry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    length_studs: float | None = None
    width_studs: float | None = None
    height_plates: float | None = None
    bounding_box_ldu: dict[str, float | None] = Field(default_factory=dict)
    geometry_source: Literal["ldraw_computed", "manually_verified", "unknown"]

class VisualFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stud_count: int | None = None
    round_hole_count: int | None = None
    axle_hole_count: int | None = None
    pin_hole_count: int | None = None
    is_curved: bool | None = None
    is_flexible: bool | None = None
    is_printed: bool | None = None
    is_assembly: bool | None = None
    feature_source: Literal["computed", "manually_verified", "unknown"]

class Color(BaseModel):
    model_config = ConfigDict(extra="forbid")
    color_id: str
    color_name: str
    source: str

class Recognition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["beta_v1", "planned", "excluded", "review_required"]
    difficulty: Literal["easy", "medium", "hard", "unknown"]
    exclusion_reason: str | None = None

class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    created_at: datetime
    updated_at: datetime
    created_by: Literal["importer", "manual_review"]
    notes: list[str] = Field(default_factory=list)

class PartRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    catalog_version: Literal["v1"]
    design_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: str
    subcategory: str | None = None
    source: Source
    ldraw: LDrawRef
    geometry: Geometry
    visual_features: VisualFeatures
    supported_colors: list[Color] = Field(default_factory=list)
    recognition: Recognition
    provenance: Provenance

def now_utc() -> datetime:
    return datetime.now(timezone.utc)
