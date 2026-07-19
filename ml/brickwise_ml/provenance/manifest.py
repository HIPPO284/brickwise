import json
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from .hashing import sha256_file

class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest_version: str
    asset_type: str
    local_path: str
    sha256: str
    byte_size: int
    source_provider: str
    source_identifier: str | None = None
    source_version: str | None = None
    retrieved_at: datetime
    imported_at: datetime
    license_raw: str | None = None
    license_status: str
    processing_steps: list[str] = Field(default_factory=list)
    parent_assets: list[str] = Field(default_factory=list)
    generated_by_tool_version: str

def manifest_for(path: Path, **meta) -> dict:
    stat = path.stat()
    payload = {"manifest_version": "1.0", "asset_type": meta.pop("asset_type", "unknown"),
               "local_path": str(path), "sha256": sha256_file(path), "byte_size": stat.st_size,
               "source_provider": meta.pop("source_provider", "unknown"),
               "source_identifier": meta.pop("source_identifier", None), "source_version": meta.pop("source_version", None),
               "retrieved_at": meta.pop("retrieved_at"), "imported_at": meta.pop("imported_at"),
               "license_raw": meta.pop("license_raw", None), "license_status": meta.pop("license_status", "unknown"),
               "processing_steps": meta.pop("processing_steps", []), "parent_assets": meta.pop("parent_assets", []),
               "generated_by_tool_version": meta.pop("generated_by_tool_version", "brickwise-ml-foundation/0.1.0")}
    return Manifest.model_validate(payload).model_dump(mode="json")

def write_manifest(path: Path, out: Path, **meta):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest_for(path, **meta), indent=2, sort_keys=True) + "\n", encoding="utf-8")
