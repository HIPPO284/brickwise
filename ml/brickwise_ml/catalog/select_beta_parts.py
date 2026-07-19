import copy
import json
from pathlib import Path
import yaml
from .models import BetaSelectionEntry, BetaSelectionOutput, PartRecord

def _config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def _norm(value: str) -> str:
    return " ".join(str(value).strip().lower().split())

def _asset_map(report: dict) -> dict:
    return {str(asset.get("design_id") or Path(asset.get("file", "")).stem): asset
            for asset in report.get("assets", [])}

def _category_group(category: str, mapping: dict) -> str | None:
    normalized = _norm(category)
    for raw, group in mapping.items():
        if _norm(raw) == normalized:
            return str(group)
    return None

def select_beta(catalog_path: Path, ldraw_report_path: Path, output: Path,
                config_path: Path | None = None, markdown_output: Path | None = None,
                target: int | None = None) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    records = catalog.get("records", catalog if isinstance(catalog, list) else [])
    config = _config(config_path) if config_path else {}
    target = target if target is not None else int(config.get("beta_target_count", 20))
    excluded = {_norm(value) for value in config.get("excluded_categories", [])}
    mapping = config.get("category_group_mapping", {})
    quotas = {str(key): int(value) for key, value in config.get("beta_category_targets", {}).items()}
    assets = _asset_map(json.loads(ldraw_report_path.read_text(encoding="utf-8")) if ldraw_report_path.exists() else {})
    eligible: list[tuple[dict, str]] = []
    rejected = []
    for source_record in records:
        record = copy.deepcopy(source_record)
        issues = []
        raw_category = str(record.get("category", ""))
        group = _category_group(raw_category, mapping)
        if _norm(raw_category) in excluded:
            issues.append("excluded category")
        if group is None:
            issues.append("review_required: unmapped category")
        features = record.get("visual_features", {})
        if features.get("is_printed") is True:
            issues.append("printed")
        if features.get("is_flexible") is True:
            issues.append("flexible")
        if features.get("is_assembly") is True:
            issues.append("assembly")
        asset = assets.get(str(record.get("design_id")))
        if asset is None:
            issues.append("missing LDraw evidence")
        else:
            if asset.get("license_status") != "accepted":
                issues.append(f"license={asset.get('license_status')}")
            if asset.get("validation_status") != "valid":
                issues.append(f"validation={asset.get('validation_status')}")
            if asset.get("missing_dependencies"):
                issues.append("missing dependencies")
        if issues:
            rejected.append({"design_id": str(record.get("design_id")), "issues": sorted(issues)})
        else:
            record["recognition"]["status"] = "beta_v1"
            record["provenance"]["notes"] = list(record["provenance"].get("notes", [])) + ["Selected by deterministic beta_v1 policy."]
            eligible.append((record, group))

    eligible.sort(key=lambda item: (item[1], str(item[0].get("design_id", ""))))
    selected_records = []
    selected_entries = []
    counts = {group: 0 for group in quotas}
    for record, group in eligible:
        if group in quotas and counts[group] >= quotas[group]:
            continue
        selected_records.append(record)
        counts[group] = counts.get(group, 0) + 1
        selected_entries.append(BetaSelectionEntry(
            part=PartRecord.model_validate(record),
            selection={"category_group": group,
                       "reason": "Accepted LDraw license, valid asset, explicit category mapping, and policy eligibility.",
                       "unresolved_review_issues": []}))
        if len(selected_records) >= target:
            break

    required = [str(value) for value in config.get("required_design_ids", [])]
    selected_ids = {str(record.get("design_id")) for record in selected_records}
    required_blockers = [value for value in required if value not in selected_ids]
    blockers = [f"Only {len(selected_records)} eligible entries; {target} required."] if len(selected_records) < target else []
    blockers += [f"Required design ID {value} is not eligible or not evidenced." for value in required_blockers]
    result = {"catalog_version": "v1", "target_count": target, "selected_count": len(selected_records),
              "blocked": bool(blockers), "category_counts": counts,
              "required_design_ids": required, "required_blockers": required_blockers,
              "records": [PartRecord.model_validate(record).model_dump(mode="json") for record in selected_records],
              "entries": [entry.model_dump(mode="json") for entry in selected_entries],
              "rejected": sorted(rejected, key=lambda item: item["design_id"]), "blockers": blockers}
    validated = BetaSelectionOutput.model_validate(result)
    serialized = validated.model_dump(mode="json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(serialized, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if markdown_output:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# Beta v1 selection", "", f"Selected: {len(selected_entries)} / {target}", "",
                 "| design_id | name | category | LDraw filename | license status | validation status | recognition difficulty | selection reason | unresolved issues |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for entry in selected_entries:
            part = entry.part
            asset = assets.get(str(part.design_id), {})
            selection = entry.selection
            lines.append("| " + " | ".join([part.design_id, part.name, part.category, str(asset.get("filename", "")),
                str(asset.get("license_status", "")), str(asset.get("validation_status", "")),
                part.recognition.difficulty, selection.reason, "; ".join(selection.unresolved_review_issues)]) + " |")
        markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return serialized
