import argparse,json
from pathlib import Path
from brickwise_ml.ldraw.asset_validator import validate_parts,write_attribution
def main():
    p=argparse.ArgumentParser(); p.add_argument("--parts-dir",required=True); p.add_argument("--policy",required=True); p.add_argument("--report",required=True); p.add_argument("--attribution")
    a=p.parse_args(); r=validate_parts(Path(a.parts_dir),Path(a.policy)); Path(a.report).parent.mkdir(parents=True,exist_ok=True); Path(a.report).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    if a.attribution: write_attribution(r,Path(a.attribution))
    print(f"assets={r['asset_count']} valid={sum(x['validation_status']=='valid' for x in r['assets'])}")
    raise SystemExit(0 if all(x["validation_status"]=="valid" for x in r["assets"]) else 1)
if __name__=="__main__": main()
