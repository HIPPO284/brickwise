import argparse,json
from pathlib import Path
from brickwise_ml.catalog.validate_catalog import validate_catalog
def main():
    p=argparse.ArgumentParser(); p.add_argument("--catalog",required=True); p.add_argument("--report")
    a=p.parse_args(); r=validate_catalog(Path(a.catalog)); print(f"valid={r['valid']} records={r['record_count']} errors={len(r['errors'])}")
    if a.report: Path(a.report).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    raise SystemExit(0 if r["valid"] else 1)
if __name__=="__main__": main()
