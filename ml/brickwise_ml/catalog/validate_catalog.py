import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from .models import PartRecord

SCHEMA = Path(__file__).with_name("schema") / "part_catalog.schema.json"

def validate_catalog(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records", data if isinstance(data, list) else [])
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = []
    for index, record in enumerate(records):
        errors.extend({"index": index, "path": list(error.path), "message": error.message}
                      for error in validator.iter_errors(record))
        try:
            PartRecord.model_validate(record)
        except Exception as exc:
            errors.append({"index": index, "path": [], "message": str(exc)})
    ids = [record.get("design_id") for record in records]
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    return {"valid": not errors and not duplicate_ids, "record_count": len(records),
            "duplicate_design_ids": duplicate_ids, "errors": errors}
