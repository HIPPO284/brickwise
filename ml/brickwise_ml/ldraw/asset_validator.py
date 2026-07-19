import fnmatch,json,hashlib,re
from pathlib import Path
from .header_parser import parse_header

def _policy(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def license_status(raw,policy):
    if not raw: return "missing"
    if raw in policy.get("accepted_exact_strings",[]): return "accepted"
    if raw in policy.get("rejected_exact_strings",[]): return "rejected"
    if any(re.search(p,raw,re.I) for p in policy.get("review_required_patterns",[])): return "review_required"
    return policy.get("default_action","review_required")
def validate_parts(parts_dir:Path,policy_path:Path)->dict:
    policy=_policy(policy_path); files=sorted(parts_dir.rglob("*.dat")) if parts_dir.exists() else []
    known={p.name.lower() for p in files}; assets=[]
    for path in files:
        h=parse_header(path); status=license_status(h["license_raw"],policy)
        missing=[d for d in h["dependencies"] if d.lower() not in known and d.lower()!=path.name.lower()]
        valid=not h["malformed_lines"] and not missing and status=="accepted"
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assets.append({"file":str(path),"filename":path.name,"sha256":digest,
                       "header_name":h["name"],"author":h["author"],"license_raw":h["license_raw"],
                       "license_status":status,"validation_status":"valid" if valid else ("review_required" if status in ("missing","review_required") else "invalid"),
                       "dependencies":h["dependencies"],"missing_dependencies":missing,
                       "malformed_lines":h["malformed_lines"],"attribution_required":True})
    return {"policy":str(policy_path),"asset_count":len(assets),"assets":assets}
def write_attribution(report:dict,path:Path):
    lines=["# LDraw attribution","", "Generated only from validated asset headers.",""]
    for a in report.get("assets",[]):
        if a["validation_status"]=="valid":
            lines += [f"## {a['filename']}",f"- Name: {a.get('header_name') or 'Not provided'}",f"- Author: {a.get('author') or 'Not provided'}",f"- License header: {a.get('license_raw') or 'Not provided'}",""]
    path.write_text("\n".join(lines),encoding="utf-8")
