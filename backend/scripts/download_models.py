"""Download the three Hugging Face models once (about 1.3 GB). They then run offline on the CPU.
Usage: python scripts/download_models.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from app import ml
except ImportError as exc:
    sys.exit(f"torch / transformers are not installed ({exc}). Install requirements-stage3.txt first.")

for kind, name in ml.MODELS.items():
    print(f"Downloading {kind}: {name} ...", flush=True)
    try:
        ml._load(kind)
        print("  ok")
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {exc}")
print("Done.")
