from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from bim_ifc_builder import BuildingPlan, build_ifc

from app.services.text_to_plan import text_to_building_plan

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"
DEFAULT_OUTPUT_FILE = "generated_model.ifc"


def _resolve_output_path(output_dir: Optional[str] = None) -> Path:
    base_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / DEFAULT_OUTPUT_FILE


def save_ifc_from_plan(plan: BuildingPlan, output_dir: Optional[str] = None) -> Path:
    output_path = _resolve_output_path(output_dir)
    return build_ifc(plan, output_path)


def save_ifc_from_text(description: str, output_dir: Optional[str] = None) -> Path:
    plan = text_to_building_plan(description)
    return save_ifc_from_plan(plan, output_dir)


def save_ifc_file(description: str, output_dir: Optional[str] = None) -> Path:
    """Backward-compatible entry point used by the text-based /ifc/generate route."""
    return save_ifc_from_text(description, output_dir)
