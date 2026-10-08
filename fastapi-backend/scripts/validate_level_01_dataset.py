"""Validate the Level 1 single-wall dataset."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "datasets" / "level-01-single-wall.jsonl"
EXPECTED_RECORD_COUNT = 50

REQUIRED_TOP_LEVEL = {
    "project",
    "site",
    "building",
    "storeys",
    "elements",
    "materials",
    "relationships",
    "metadata",
}

REQUIRED_ELEMENT_COLLECTIONS = {
    "walls",
    "slabs",
    "columns",
    "beams",
    "doors",
    "windows",
    "roofs",
    "stairs",
    "spaces",
}

EMPTY_ELEMENT_COLLECTIONS = REQUIRED_ELEMENT_COLLECTIONS - {"walls"}


def _distance(start: list[float], end: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(start, end)))


def validate_record(record: dict, line_number: int) -> list[str]:
    errors: list[str] = []
    prefix = f"Line {line_number}"

    if set(record.keys()) != {"input", "output"}:
        errors.append(f"{prefix}: record must contain only 'input' and 'output'")
        return errors

    if not isinstance(record["input"], str) or not record["input"].strip():
        errors.append(f"{prefix}: 'input' must be a non-empty string")

    output = record.get("output")
    if not isinstance(output, dict):
        errors.append(f"{prefix}: 'output' must be an object")
        return errors

    missing = REQUIRED_TOP_LEVEL - set(output.keys())
    if missing:
        errors.append(f"{prefix}: missing top-level keys: {sorted(missing)}")

    extra = set(output.keys()) - REQUIRED_TOP_LEVEL
    if extra:
        errors.append(f"{prefix}: unexpected top-level keys: {sorted(extra)}")

    if output.get("materials") != []:
        errors.append(f"{prefix}: 'materials' must be an empty list at Level 1")

    if output.get("relationships") != []:
        errors.append(f"{prefix}: 'relationships' must be an empty list at Level 1")

    metadata = output.get("metadata", {})
    if metadata.get("units") != "meters":
        errors.append(f"{prefix}: metadata.units must be 'meters'")
    if metadata.get("coordinate_system") != "right_handed_z_up":
        errors.append(f"{prefix}: metadata.coordinate_system must be 'right_handed_z_up'")

    storeys = output.get("storeys", [])
    if not isinstance(storeys, list) or len(storeys) != 1:
        errors.append(f"{prefix}: exactly one storey is required")
        return errors

    storey = storeys[0]
    storey_id = storey.get("id")
    if not storey_id:
        errors.append(f"{prefix}: storey id is required")

    building = output.get("building", {})
    building_storeys = building.get("storeys", [])
    if building_storeys != [storey_id]:
        errors.append(
            f"{prefix}: building.storeys must reference the single storey id '{storey_id}'"
        )

    elements = output.get("elements", {})
    if set(elements.keys()) != REQUIRED_ELEMENT_COLLECTIONS:
        errors.append(f"{prefix}: elements must contain all expected collections")

    for collection in EMPTY_ELEMENT_COLLECTIONS:
        if elements.get(collection) != []:
            errors.append(f"{prefix}: elements.{collection} must be empty at Level 1")

    walls = elements.get("walls", [])
    if not isinstance(walls, list) or len(walls) != 1:
        errors.append(f"{prefix}: exactly one wall is required")
        return errors

    wall = walls[0]
    if wall.get("storey") != storey_id:
        errors.append(f"{prefix}: wall.storey must match storey id '{storey_id}'")

    geometry = wall.get("geometry", {})
    start = geometry.get("start")
    end = geometry.get("end")
    height = geometry.get("height")
    thickness = geometry.get("thickness")

    if not (isinstance(start, list) and len(start) == 3):
        errors.append(f"{prefix}: wall geometry.start must be a 3-element list")
    if not (isinstance(end, list) and len(end) == 3):
        errors.append(f"{prefix}: wall geometry.end must be a 3-element list")

    if isinstance(start, list) and isinstance(end, list) and len(start) == 3 and len(end) == 3:
        if start == end:
            errors.append(f"{prefix}: wall start and end must be distinct")
        elif _distance(start, end) <= 0:
            errors.append(f"{prefix}: wall length must be greater than zero")

    if not isinstance(height, (int, float)) or height <= 0:
        errors.append(f"{prefix}: wall height must be a positive number")
    if not isinstance(thickness, (int, float)) or thickness <= 0:
        errors.append(f"{prefix}: wall thickness must be a positive number")

    ids = [
        output.get("project", {}).get("id"),
        output.get("site", {}).get("id"),
        building.get("id"),
        storey_id,
        wall.get("id"),
    ]
    if any(not item for item in ids):
        errors.append(f"{prefix}: project, site, building, storey, and wall ids are required")
    if len(set(ids)) != len(ids):
        errors.append(f"{prefix}: ids must be unique within the record")

    return errors


def validate_dataset(path: Path = DATASET_PATH) -> list[str]:
    if not path.exists():
        return [f"Dataset not found: {path}"]

    errors: list[str] = []
    records: list[dict] = []

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(f"Line {line_number}: invalid JSON ({exc})")
                continue
            records.append(record)
            errors.extend(validate_record(record, line_number))

    if len(records) != EXPECTED_RECORD_COUNT:
        errors.append(
            f"Expected {EXPECTED_RECORD_COUNT} records, found {len(records)}"
        )

    return errors


def main() -> int:
    errors = validate_dataset()
    if errors:
        print("Level 1 dataset validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"Validated {EXPECTED_RECORD_COUNT} records in {DATASET_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
