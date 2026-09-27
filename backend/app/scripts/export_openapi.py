"""Write backend/openapi.json so the frontend can generate TypeScript types.
Run from backend/:  python -m app.scripts.export_openapi
"""
import json
from pathlib import Path

from app.main import app

out = Path(__file__).resolve().parents[2] / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2) + "\n")
print(f"Wrote {out}")
