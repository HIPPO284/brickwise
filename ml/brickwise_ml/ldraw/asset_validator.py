import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from .header_parser import parse_header

def _policy(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def license_status(raw: str | None, policy: dict) -> str:
    if not raw: return "missing"
    if raw in policy.get("accepted_exact_strings", []): return "accepted"
    if raw in policy.get("rejected_exact_strings", []): return "rejected"
    if any(re.search(pattern, raw, re.I) for pattern in policy.get("review_required_patterns", [])): return "review_required"
    return policy.get("default_action", "review_required")

def _norm(value: str) -> str:
    return value.replace("\\", "/").lstrip("./").lower()

def _resolve(reference: str, current: Path, root: Path, by_rel: dict[str, Path]) -> Path | None:
    normalized = _norm(reference)
    candidates = [_norm(str((current.parent / reference).relative_to(root))) if (current.parent / reference).exists() else "",
                  normalized, _norm("parts/" + normalized), _norm("p/" + normalized)]
    for candidate in candidates:
        if candidate and candidate in by_rel: return by_rel[candidate]
    basename = Path(normalized).name
    matches = [path for rel, path in by_rel.items() if Path(rel).name == basename]
    return matches[0] if len(matches) == 1 else None

def validate_parts(parts_dir: Path, policy_path: Path) -> dict:
    policy = _policy(policy_path)
    files = sorted(parts_dir.rglob("*.dat")) if parts_dir.exists() else []
    by_rel = {_norm(str(path.relative_to(parts_dir))): path for path in files}
    parsed = {path: parse_header(path) for path in files}
    cycles, missing_by_file, parents = set(), {}, {}
    def visit(path: Path, stack: list[Path]):
        if path in stack:
            cycles.add(" -> ".join(item.name for item in stack[stack.index(path):] + [path]))
            return
        for reference in parsed[path]["dependencies"]:
            dependency = _resolve(reference, path, parts_dir, by_rel)
            if dependency is None:
                missing_by_file.setdefault(path, []).append(reference)
                continue
            parents.setdefault(str(dependency), []).append(str(path))
            if dependency not in parsed: parsed[dependency] = parse_header(dependency)
            visit(dependency, stack + [path])
    for path in files: visit(path, [])
    assets = []
    for path in files:
        header = parsed[path]
        status = license_status(header["license_raw"], policy)
        missing = sorted(set(missing_by_file.get(path, [])))
        invalid = bool(header["malformed_lines"] or missing or status == "rejected")
        validation = "valid" if status == "accepted" and not invalid else ("review_required" if status in ("missing", "review_required") else "invalid")
        dependency_hashes = {}
        for reference in header["dependencies"]:
            dependency = _resolve(reference, path, parts_dir, by_rel)
            if dependency and dependency.exists(): dependency_hashes[reference] = hashlib.sha256(dependency.read_bytes()).hexdigest()
        assets.append({"file": str(path), "filename": path.name, "relative_path": str(path.relative_to(parts_dir)).replace("\\", "/"),
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "header_name": header["name"],
                       "author": header["author"], "license_raw": header["license_raw"], "raw_header": header["raw_header"],
                       "license_status": status, "validation_status": validation, "dependencies": header["dependencies"],
                       "dependency_sha256": dependency_hashes, "missing_dependencies": missing,
                       "parents": sorted(parents.get(str(path), [])), "malformed_lines": header["malformed_lines"],
                       "attribution_required": True})
    return {"policy": str(policy_path), "asset_count": len(assets), "validated_at": datetime.now(timezone.utc).isoformat(),
            "cycles": sorted(cycles), "assets": assets}

def write_human_report(report: dict, path: Path):
    lines = ["# LDraw validation report", "", f"Assets: {report.get('asset_count', 0)}", f"Cycles: {len(report.get('cycles', []))}", ""]
    for asset in report.get("assets", []):
        lines.append(f"- {asset['relative_path']}: {asset['validation_status']} ({asset['license_status']})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def write_attribution(report: dict, path: Path):
    lines = ["# LDraw attribution", "", "Generated only from parsed asset headers.", ""]
    for asset in report.get("assets", []):
        if asset["validation_status"] == "valid":
            lines += [f"## {asset['relative_path']}", f"- Name: {asset.get('header_name') or 'Not provided'}",
                      f"- Author: {asset.get('author') or 'Not provided'}",
                      f"- License header: {asset.get('license_raw') or 'Not provided'}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
