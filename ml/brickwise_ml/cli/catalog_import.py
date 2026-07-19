import argparse
from pathlib import Path
from brickwise_ml.catalog.import_rebrickable import import_csv, api_import

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["csv", "api"], required=True)
    parser.add_argument("--parts-csv")
    parser.add_argument("--colors-csv")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report")
    parser.add_argument("--timestamp")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.mode == "api":
        api_import()
    if not args.parts_csv:
        parser.error("--parts-csv is required for csv mode")
    result = import_csv(Path(args.parts_csv), Path(args.output),
                        Path(args.colors_csv) if args.colors_csv else None,
                        args.dry_run, args.timestamp, Path(args.report) if args.report else None)
    report = result["import_report"]
    print(f"records={report['record_count']} errors={len(report['errors'])} duplicates={len(report['duplicates'])} dry_run={args.dry_run}")

if __name__ == "__main__":
    main()
