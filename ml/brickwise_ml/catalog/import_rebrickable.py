import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from .models import PartRecord

IMAGE_FIELDS = {"image_url", "part_img_url", "part_img", "image", "image_path"}

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _value(row: dict, *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value).strip()
    return ""

def deterministic_timestamp(source: Path, timestamp: str | None = None) -> str:
    raw = timestamp or os.getenv("SOURCE_DATE_EPOCH")
    if raw is not None:
        if raw.isdigit():
            return datetime.fromtimestamp(int(raw), timezone.utc).isoformat()
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value.astimezone(timezone.utc).isoformat()
    return datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat()

def _read_colors(path: Path | None) -> dict[str, list[dict]]:
    if not path:
        return {}
    colors: dict[str, list[dict]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            design_id = _value(row, "design_id", "part_num", "part_number")
            color_id = _value(row, "color_id", "color_num", "color")
            color_name = _value(row, "color_name", "name")
            if design_id and color_id and color_name:
                colors.setdefault(design_id, []).append({"color_id": color_id, "color_name": color_name, "source": str(path)})
    return colors

def import_csv(parts_csv: Path, output: Path, colors_csv: Path | None = None,
               dry_run: bool = False, timestamp: str | None = None,
               report_output: Path | None = None) -> dict:
    if isinstance(colors_csv, bool):
        dry_run, colors_csv = colors_csv, None
    retrieved_at = deterministic_timestamp(parts_csv, timestamp)
    imported_at = retrieved_at
    source_hash = sha256_file(parts_csv)
    color_map = _read_colors(colors_csv)
    records: list[PartRecord] = []
    errors: list[dict] = []
    duplicates: list[str] = []
    names_by_id: dict[str, set[str]] = {}
    seen: set[str] = set()
    with parts_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            errors.append({"line": 1, "reason": "missing CSV header"})
        for line_no, row in enumerate(reader, 2):
            design_id = _value(row, "design_id", "part_num", "part_number")
            name = _value(row, "name", "part_name")
            if not design_id:
                errors.append({"line": line_no, "reason": "missing design_id"})
                continue
            if not name:
                errors.append({"line": line_no, "design_id": design_id, "reason": "missing name"})
                continue
            design_id = str(design_id)
            names_by_id.setdefault(design_id, set()).add(name)
            if design_id in seen:
                duplicates.append(design_id)
                continue
            seen.add(design_id)
            records.append(PartRecord(
                schema_version="1.0", catalog_version="v1", design_id=design_id,
                name=name, aliases=[], category=_value(row, "category") or "unknown",
                subcategory=_value(row, "subcategory") or None,
                source={"provider": "rebrickable_csv", "source_record_id": design_id,
                        "retrieved_at": retrieved_at, "source_version": None, "source_sha256": source_hash},
                ldraw={"filename": None, "file_sha256": None, "header_name": None, "license_raw": None,
                       "license_status": "missing", "attribution_required": True, "validation_status": "missing"},
                geometry={"length_studs": None, "width_studs": None, "height_plates": None,
                          "bounding_box_ldu": {"x": None, "y": None, "z": None}, "geometry_source": "unknown"},
                visual_features={"stud_count": None, "round_hole_count": None, "axle_hole_count": None,
                                 "pin_hole_count": None, "is_curved": None, "is_flexible": None,
                                 "is_printed": None, "is_assembly": None, "feature_source": "unknown"},
                supported_colors=sorted(color_map.get(design_id, []), key=lambda c: (c["color_id"], c["color_name"])),
                recognition={"status": "planned", "difficulty": "unknown", "exclusion_reason": None},
                provenance={"created_at": retrieved_at, "updated_at": retrieved_at, "created_by": "importer",
                            "notes": ["Imported from permitted metadata CSV; image fields ignored."]}
            ))
    conflicts = {design_id: sorted(names) for design_id, names in names_by_id.items() if len(names) > 1}
    records_json = [record.model_dump(mode="json") for record in sorted(records, key=lambda record: record.design_id)]
    result = {
        "schema_version": "1.0", "catalog_version": "v1", "records": records_json,
        "import_report": {"source_file": str(parts_csv), "source_sha256": source_hash,
                          "colors_file": str(colors_csv) if colors_csv else None,
                          "retrieved_at": retrieved_at, "imported_at": imported_at,
                          "record_count": len(records_json), "errors": errors,
                          "duplicates": sorted(set(duplicates)), "conflicts": conflicts,
                          "image_fields_ignored_count": len(IMAGE_FIELDS), "network_requests": 0}
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if report_output:
        report_output.parent.mkdir(parents=True, exist_ok=True)
        report_output.write_text(json.dumps(result["import_report"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    return result

def api_import(*_, **__):
    raise RuntimeError("API mode is an explicit adapter stub; CSV mode performs no network requests.")
