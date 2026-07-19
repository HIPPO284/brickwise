import json
from pathlib import Path

def select_beta(catalog_path:Path, ldraw_report_path:Path, output:Path, target=20):
    catalog=json.loads(catalog_path.read_text(encoding="utf-8"))
    records=catalog.get("records",catalog if isinstance(catalog,list) else [])
    report=json.loads(ldraw_report_path.read_text(encoding="utf-8")) if ldraw_report_path.exists() else {"assets":[]}
    valid={a.get("design_id") or Path(a.get("file","")).stem:a for a in report.get("assets",[])}
    eligible=[]
    for r in records:
        a=valid.get(r.get("design_id"))
        if r.get("recognition",{}).get("status")=="excluded": continue
        if a and a.get("license_status")=="accepted" and a.get("validation_status")=="valid":
            eligible.append(r)
    eligible.sort(key=lambda r:(r.get("category",""),r.get("design_id","")))
    selected=eligible[:target]
    result={"catalog_version":"v1","target_count":target,"selected_count":len(selected),
            "records":selected,"blocked":len(selected)<target,
            "blockers":[] if len(selected)>=target else [f"Only {len(selected)} entries have accepted, valid LDraw assets; {target} required."]}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result
