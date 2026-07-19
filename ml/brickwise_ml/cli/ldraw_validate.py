import argparse
import json
from pathlib import Path
from brickwise_ml.ldraw.asset_validator import validate_parts, write_attribution, write_human_report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parts-dir", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--human-report")
    parser.add_argument("--attribution")
    args = parser.parse_args()
    report = validate_parts(Path(args.parts_dir), Path(args.policy))
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.human_report: write_human_report(report, Path(args.human_report))
    if args.attribution: write_attribution(report, Path(args.attribution))
    valid = all(asset["validation_status"] == "valid" for asset in report["assets"]) and not report["cycles"]
    print(f"assets={report['asset_count']} valid={sum(a['validation_status']=='valid' for a in report['assets'])} cycles={len(report['cycles'])}")
    raise SystemExit(0 if valid else 1)

if __name__ == "__main__":
    main()
