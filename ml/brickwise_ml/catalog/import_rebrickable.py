import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from .models import PartRecord

IMAGE_FIELDS = {"image_url", "part_img_url", "part_img", "image", "image_path"}

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()

def _value(row, *names):
    for name in names:
        if row.get(name) not in (None, ""): return str(row[name]).strip()
    return ""

def import_csv(parts_csv: Path, output: Path, dry_run=False) -> dict:
    retrieved = datetime.now(timezone.utc).isoformat()
    records, errors, duplicates, conflicts = [], [], [], {}
    with parts_csv.open(newline="", encoding="utf-8-sig") as f:
        for line_no,row in enumerate(csv.DictReader(f), 2):
            design_id=_value(row,"design_id","part_num","part_number")
            name=_value(row,"name","part_name")
            if not design_id or not name:
                errors.append({"line":line_no,"reason":"missing design_id or name"}); continue
            if design_id in conflicts: conflicts[design_id].append(name)
            else: conflicts[design_id]=[name]
            if any(r.design_id==design_id for r in records):
                duplicates.append(design_id); continue
            stamp=retrieved
            records.append(PartRecord(
                schema_version="1.0",catalog_version="v1",design_id=str(design_id),
                name=name,aliases=[],category=_value(row,"category") or "unknown",
                subcategory=_value(row,"subcategory") or None,
                source={"provider":"rebrickable_csv","source_record_id":str(design_id),
                        "retrieved_at":stamp,"source_version":None,"source_sha256":sha256_file(parts_csv)},
                ldraw={"filename":None,"file_sha256":None,"header_name":None,"license_raw":None,
                       "license_status":"missing","attribution_required":True,"validation_status":"missing"},
                geometry={"length_studs":None,"width_studs":None,"height_plates":None,
                          "bounding_box_ldu":{},"geometry_source":"unknown"},
                visual_features={"stud_count":None,"round_hole_count":None,"axle_hole_count":None,
                                 "pin_hole_count":None,"is_curved":None,"is_flexible":None,
                                 "is_printed":None,"is_assembly":None,"feature_source":"unknown"},
                supported_colors=[],recognition={"status":"planned","difficulty":"unknown","exclusion_reason":None},
                provenance={"created_at":stamp,"updated_at":stamp,"created_by":"importer",
                            "notes":["Imported from permitted metadata CSV; image fields ignored."]}
            ))
    for key,names in conflicts.items():
        if len(set(names))>1: conflicts[key]=names
        else: del conflicts[key]
    result={"schema_version":"1.0","catalog_version":"v1",
             "records":[r.model_dump(mode="json") for r in sorted(records,key=lambda x:x.design_id)],
             "import_report":{"source_file":str(parts_csv),"source_sha256":sha256_file(parts_csv),
                              "retrieved_at":retrieved,"record_count":len(records),"errors":errors,
                              "duplicates":sorted(set(duplicates)),"conflicts":conflicts}}
    if not dry_run:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result

def api_import(*_, **__):
    raise RuntimeError("API mode is an explicit adapter stub. Supply official API documentation and credentials; no image download is implemented.")
