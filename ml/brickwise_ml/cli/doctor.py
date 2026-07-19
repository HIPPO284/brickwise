import argparse
import importlib.util
import os
import sys
from pathlib import Path

def check(name, ok, detail, required=True):
    return {"name": name, "status": "PASS" if ok else ("FAIL" if required else "WARN"), "detail": detail}

def run_checks(root: Path | None = None) -> list[dict]:
    root = root or Path(__file__).resolve().parents[2]
    checks = [check("python", sys.version_info >= (3, 11) and sys.version_info < (3, 14), platform_version()),
              check("pydantic", importlib.util.find_spec("pydantic") is not None, "importable"),
              check("jsonschema", importlib.util.find_spec("jsonschema") is not None, "importable"),
              check("yaml", importlib.util.find_spec("yaml") is not None, "importable"),
              check("config", (root / "config" / "approved_licenses.example.json").is_file(), "license policy"),
              check("catalog path", (root / "data" / "catalog").is_dir(), "catalog directory"),
              check("custom model", os.getenv("CUSTOM_MODEL_ENABLED", "false").lower() == "false", "must remain false"),
              check("api key", bool(os.getenv("REBRICKABLE_API_KEY")), "present but never printed", required=False),
              check("ldraw path", not os.getenv("LDRAW_PARTS_DIR") or Path(os.environ["LDRAW_PARTS_DIR"]).is_dir(), "configured path", required=False),
              check("production sqlite isolation", not (root.parent / "data" / "brickwise.sqlite").exists(), "ML must not use production DB")]
    return checks

def platform_version(): return sys.version.split()[0]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    args = parser.parse_args()
    checks = run_checks(Path(args.root) if args.root else None)
    for item in checks: print(f"{item['status']} {item['name']}: {item['detail']}")
    return 1 if any(item["status"] == "FAIL" for item in checks) else 0

if __name__ == "__main__": raise SystemExit(main())
