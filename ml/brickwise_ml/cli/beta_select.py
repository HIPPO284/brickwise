import argparse
from pathlib import Path
from brickwise_ml.catalog.select_beta_parts import select_beta

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--ldraw-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", default="config/catalog_selection_v1.yaml")
    parser.add_argument("--markdown-output")
    parser.add_argument("--target", type=int)
    args = parser.parse_args()
    result = select_beta(Path(args.catalog), Path(args.ldraw_report), Path(args.output),
                         Path(args.config), Path(args.markdown_output) if args.markdown_output else None, args.target)
    print(f"selected={result['selected_count']} target={result['target_count']} blocked={result['blocked']}")
    raise SystemExit(0 if not result["blocked"] else 1)

if __name__ == "__main__":
    main()
