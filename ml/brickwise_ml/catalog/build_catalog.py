"""Deterministic catalog assembly helpers."""
import json
from pathlib import Path
def build(records, output:Path):
    ordered=sorted(records,key=lambda r:str(r.get("design_id","")))
    payload={"schema_version":"1.0","catalog_version":"v1","records":ordered}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return payload
