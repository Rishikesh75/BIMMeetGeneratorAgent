"""Bridge to the repo-root cityjson_to_ifc.py converter.

That script lives outside the fastapi-backend package (one level above it),
so it is loaded by path instead of being duplicated here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
CONVERTER_PATH = REPO_ROOT / "cityjson_to_ifc.py"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"
OUTPUT_FILE = "generated_from_doc.ifc"


def _load_converter() -> Any:
    module_name = "cityjson_to_ifc"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, CONVERTER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load cityjson_to_ifc.py from {CONVERTER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def save_ifc_from_cityjson(cityjson: dict[str, Any]) -> tuple[Path, int]:
    """Write the CityJSON model to IFC and return (output_path, city_object_count)."""
    converter = _load_converter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / OUTPUT_FILE
    count = converter.build_ifc(cityjson, output_path)
    return output_path, count
