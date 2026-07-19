import argparse
from pathlib import Path
from brickwise_ml.catalog.select_beta_parts import select_beta
def main():
    p=argparse.ArgumentParser(); p.add_argument("--catalog",required=True); p.add_argument("--ldraw-report",required=True); p.add_argument("--output",required=True); p.add_argument("--target",type=int,default=20)
    a=p.parse_args(); r=select_beta(Path(a.catalog),Path(a.ldraw_report),Path(a.output),a.target); print(f"selected={r['selected_count']} target={r['target_count']} blocked={r['blocked']}")
    raise SystemExit(0 if not r["blocked"] else 1)
if __name__=="__main__": main()
