import argparse
from pathlib import Path
from brickwise_ml.catalog.import_rebrickable import import_csv,api_import
def main():
    p=argparse.ArgumentParser(); p.add_argument("--mode",choices=["csv","api"],required=True); p.add_argument("--parts-csv"); p.add_argument("--output",required=True); p.add_argument("--dry-run",action="store_true")
    a=p.parse_args()
    if a.mode=="api": api_import()
    if not a.parts_csv: p.error("--parts-csv is required for csv mode")
    r=import_csv(Path(a.parts_csv),Path(a.output),a.dry_run); print(f"records={r['import_report']['record_count']} errors={len(r['import_report']['errors'])} dry_run={a.dry_run}")
if __name__=="__main__": main()
