import os,sys
from pathlib import Path
def main():
    root=Path(__file__).resolve().parents[2]
    checks={"python":sys.version.split()[0],"custom_model_enabled":os.getenv("CUSTOM_MODEL_ENABLED","false"),
            "api_key_present":bool(os.getenv("REBRICKABLE_API_KEY")),"ldraw_path":os.getenv("LDRAW_PARTS_DIR",""),
            "config_exists":(root/"config").exists(),"catalog_exists":(root/"data/catalog").exists()}
    for k,v in checks.items(): print(f"{k}: {v}")
    return 0
if __name__=="__main__": raise SystemExit(main())
