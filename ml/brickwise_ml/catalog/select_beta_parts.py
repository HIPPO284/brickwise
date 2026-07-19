import copy
import json
from pathlib import Path
import yaml

def _config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def _asset_map(report: dict) -> dict:
    result = {}
    for asset in report.get("assets", []):
        result[asset.get("design_id") or Path(asset.get("file", "")).stem] = asset
    return result

def select_beta(catalog_path: Path, ldraw_report_path: Path, output: Path,
                config_path: Path | None = None, markdown_output: Path | None = None,
                target: int | None = None) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    records = catalog.get("records", catalog if isinstance(catalog, list) else [])
    config = _config(config_path) if config_path else {}
    target = target if target is not None else int(config.get("beta_target_count", 20))
    excluded = {str(value).lower() for value in config.get("excluded_categories", [])}
    assets = _asset_map(json.loads(ldraw_report_path.read_text(encoding="utf-8")) if ldraw_report_path.exists() else {})
    eligible = []
    rejected = []
    for record in records:
        issues = []
        category = str(record.get("category", "")).lower()
        asset = assets.get(str(record.get("design_id")))
        if category in excluded: issues.append("excluded category")
        features = record.get("visual_features", {})
        if features.get("is_printed") is True: issues.append("printed")
        if features.get("is_flexible") is True: issues.append("flexible")
        if features.get("is_assembly") is True: issues.append("assembly")
        if asset is None: issues.append("missing LDraw evidence")
        else:
            if asset.get("license_status") != "accepted": issues.append(f"license={asset.get('license_status')}")
            if asset.get("validation_status") != "valid": issues.append(f"validation={asset.get('validation_status')}")
            if asset.get("missing_dependencies"): issues.append("missing dependencies")
        if issues:
            rejected.append({"design_id": str(record.get("design_id")), "issues": issues})
        else:
            selected = copy.deepcopy(record)
            selected["recognition"]["status"] = "beta_v1"
            selected["provenance"]["notes"] = list(selected["provenance"].get("notes", [])) + ["Selected by deterministic beta_v1 policy."]
            selected["selection_reason"] = "Accepted LDraw license, valid asset, rigid unprinted geometry, and policy eligibility."
            selected["unresolved_review_issues"] = []
            eligible.append(selected)
    eligible.sort(key=lambda record: (str(record.get("category", "")), str(record.get("design_id", ""))))
    quotas = config.get("beta_category_targets", {})
    selected = []
    counts = {str(key): 0 for key in quotas}
    for record in eligible:
        category = str(record.get("category", ""))
        quota = quotas.get(category)
        if quota is not None and counts.get(category, 0) >= int(quota): continue
        selected.append(record)
        if category in counts: counts[category] += 1
        if len(selected) >= target: break
    required = [str(value) for value in config.get("required_design_ids", [])]
    selected_ids = {str(record.get("design_id")) for record in selected}
    required_blockers = [value for value in required if value not in selected_ids]
    blockers = [f"Only {len(selected)} eligible entries; {target} required."] if len(selected) < target else []
    blockers += [f"Required design ID {value} is not eligible or not evidenced." for value in required_blockers]
    result = {"catalog_version": "v1", "target_count": target, "selected_count": len(selected),
              "records": selected, "blocked": bool(blockers), "category_counts": counts,
              "required_design_ids": required, "required_blockers": required_blockers,
              "rejected": sorted(rejected, key=lambda item: item["design_id"]), "blockers": blockers}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if markdown_output:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Beta v1 selection", "", f"Selected: {len(selected)} / {target}", "", "| design_id | name | category | LDraw filename | license status | validation status | recognition difficulty | selection reason | unresolved issues |", "|---|---|---|---|---|---|---|---|---|"]
        for record in selected:
            asset = assets.get(str(record["design_id"]), {})
            lines.append("| " + " | ".join([str(record["design_id"]), record["name"], record["category"], str(asset.get("filename", "")), str(asset.get("license_status", "")), str(asset.get("validation_status", "")), record["recognition"].get("difficulty", "unknown"), record.get("selection_reason", ""), "; ".join(record.get("unresolved_review_issues", []))]) + " |")
        markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result
