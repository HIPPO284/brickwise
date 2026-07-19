from pathlib import Path
import os

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ML_ROOT = PACKAGE_ROOT
REPO_ROOT = ML_ROOT.parent
CUSTOM_MODEL_ENABLED = os.getenv("CUSTOM_MODEL_ENABLED", "false").lower() == "true"
