import json
from pathlib import Path
from brickwise_ml.catalog.select_beta_parts import select_beta
from brickwise_ml.provenance.hashing import sha256_file
ROOT=Path(__file__).parents[1]
def test_beta_blocks_without_valid_assets(tmp_path):
    c=ROOT/"data/catalog/catalog.v1.example.json"; report=tmp_path/"r.json"; report.write_text('{"assets":[]}')
    out=tmp_path/"b.json"; r=select_beta(c,report,out); assert r["blocked"]; assert r["selected_count"]==0
def test_hash_changes(tmp_path):
    p=tmp_path/"x"; p.write_text("a"); one=sha256_file(p); p.write_text("b"); assert one!=sha256_file(p)
