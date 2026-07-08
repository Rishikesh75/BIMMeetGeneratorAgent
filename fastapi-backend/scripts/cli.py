from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bim_ifc_builder import BuildingPlan, build_ifc
from pydantic import ValidationError


def load_building_plan(json_path: Path) -> BuildingPlan:
    raw = json_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return BuildingPlan.model_validate(data)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a BIM building plan JSON file into an IFC file using bim_ifc_builder."
    )
    parser.add_argument(
        "input_json",
        type=Path,
        help="Path to the input building plan JSON file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("output/generated_model.ifc"),
        help="Output IFC file path. Defaults to output/generated_model.ifc.",
    )

    args = parser.parse_args()

    try:
        plan = load_building_plan(args.input_json)
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {args.input_json}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON: {exc}")
        return 1
    except ValidationError as exc:
        print("ERROR: Building plan validation failed:")
        print(exc)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path = build_ifc(plan, args.output)
    except Exception as exc:
        print(f"ERROR: Failed to build IFC: {exc}")
        return 1

    print(f"IFC file generated successfully: {output_path}")
    print(f"Element count: {len(plan.elements)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
