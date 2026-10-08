"""Validate cumulative BIM datasets for Levels 2 through 10."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dataset_common import (
    ELEMENT_COLLECTIONS,
    LEVEL_FILES,
    REQUIRED_TOP_LEVEL,
    collect_element_ids,
    distance,
    outline_area,
    wall_length,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = REPO_ROOT / "datasets"
RECORDS_PER_LEVEL = 50

STRUCTURAL_COLLECTIONS = ("walls", "slabs", "columns", "beams")
OPENING_COLLECTIONS = ("doors", "windows")


def _prefix(level: int, line_number: int, dataset_name: str) -> str:
    return f"{dataset_name} line {line_number}"


def _validate_base(record: dict, level: int, line_number: int, dataset_name: str) -> list[str]:
    errors: list[str] = []
    p = _prefix(level, line_number, dataset_name)

    if set(record.keys()) != {"input", "output"}:
        errors.append(f"{p}: record must contain only 'input' and 'output'")
        return errors

    if not isinstance(record["input"], str) or not record["input"].strip():
        errors.append(f"{p}: 'input' must be a non-empty string")

    output = record.get("output")
    if not isinstance(output, dict):
        errors.append(f"{p}: 'output' must be an object")
        return errors

    if set(output.keys()) != set(REQUIRED_TOP_LEVEL):
        errors.append(f"{p}: unexpected top-level keys")

    metadata = output.get("metadata", {})
    if metadata.get("units") != "meters":
        errors.append(f"{p}: metadata.units must be 'meters'")
    if metadata.get("coordinate_system") != "right_handed_z_up":
        errors.append(f"{p}: metadata.coordinate_system must be 'right_handed_z_up'")
    if metadata.get("dataset_level") != level:
        errors.append(f"{p}: metadata.dataset_level must be {level}")

    storeys = output.get("storeys", [])
    building_storeys = output.get("building", {}).get("storeys", [])
    storey_ids = [storey.get("id") for storey in storeys]
    if building_storeys != storey_ids:
        errors.append(f"{p}: building.storeys must match storeys ids")

    elements = output.get("elements", {})
    if set(elements.keys()) != set(ELEMENT_COLLECTIONS):
        errors.append(f"{p}: elements must contain all expected collections")

    filled_ids: list[str] = []
    for key in ("project", "site", "building"):
        item_id = output.get(key, {}).get("id")
        if item_id:
            filled_ids.append(item_id)
    for storey in storeys:
        if storey.get("id"):
            filled_ids.append(storey["id"])
    for collection in ELEMENT_COLLECTIONS:
        for element in elements.get(collection, []):
            if element.get("id"):
                filled_ids.append(element["id"])
    for material in output.get("materials", []):
        if material.get("id"):
            filled_ids.append(material["id"])
    for relationship in output.get("relationships", []):
        if relationship.get("id"):
            filled_ids.append(relationship["id"])
    if len(filled_ids) != len(set(filled_ids)):
        errors.append(f"{p}: ids must be unique within the record")

    for wall in elements.get("walls", []):
        geometry = wall.get("geometry", {})
        start = geometry.get("start")
        end = geometry.get("end")
        if not (isinstance(start, list) and len(start) == 3):
            errors.append(f"{p}: wall {wall.get('id')} start must be 3D")
        if not (isinstance(end, list) and len(end) == 3):
            errors.append(f"{p}: wall {wall.get('id')} end must be 3D")
        if isinstance(start, list) and isinstance(end, list) and start == end:
            errors.append(f"{p}: wall {wall.get('id')} start/end must differ")
        if geometry.get("height", 0) <= 0 or geometry.get("thickness", 0) <= 0:
            errors.append(f"{p}: wall {wall.get('id')} height/thickness must be positive")

    for slab in elements.get("slabs", []):
        outline = slab.get("outline", [])
        if len(outline) < 3 or outline_area(outline) <= 0:
            errors.append(f"{p}: slab {slab.get('id')} outline must be non-degenerate")
        if slab.get("thickness", 0) <= 0:
            errors.append(f"{p}: slab {slab.get('id')} thickness must be positive")

    for roof in elements.get("roofs", []):
        outline = roof.get("outline", [])
        if len(outline) < 3 or outline_area(outline) <= 0:
            errors.append(f"{p}: roof {roof.get('id')} outline must be non-degenerate")

    for column in elements.get("columns", []):
        for dim in ("width", "depth", "height"):
            if column.get(dim, 0) <= 0:
                errors.append(f"{p}: column {column.get('id')} {dim} must be positive")

    for beam in elements.get("beams", []):
        start = beam.get("start")
        end = beam.get("end")
        if not (isinstance(start, list) and isinstance(end, list) and start != end):
            errors.append(f"{p}: beam {beam.get('id')} must have distinct start/end")
        if beam.get("width", 0) <= 0 or beam.get("height", 0) <= 0:
            errors.append(f"{p}: beam {beam.get('id')} dimensions must be positive")

    return errors


def _count_structural(elements: dict) -> int:
    return sum(len(elements[name]) for name in STRUCTURAL_COLLECTIONS)


def _has_geometry_variation(elements: dict) -> bool:
    for wall in elements.get("walls", []):
        start = wall["geometry"]["start"]
        end = wall["geometry"]["end"]
        if start[0] != end[0] and start[1] != end[1]:
            return True
    for slab in elements.get("slabs", []):
        if len(slab.get("outline", [])) > 4:
            return True
    for beam in elements.get("beams", []):
        start = beam.get("start", [])
        end = beam.get("end", [])
        if len(start) == 3 and len(end) == 3 and start[0] != end[0] and start[1] != end[1]:
            return True
    if elements.get("roofs"):
        return True
    return False


def _validate_openings(elements: dict, p: str) -> list[str]:
    errors: list[str] = []
    walls_by_id = {wall["id"]: wall for wall in elements.get("walls", [])}

    for collection in OPENING_COLLECTIONS:
        for opening in elements.get(collection, []):
            host = opening.get("host_wall")
            if host not in walls_by_id:
                errors.append(f"{p}: {collection[:-1]} {opening.get('id')} has invalid host_wall")
                continue
            wall = walls_by_id[host]
            wlen = wall_length(wall)
            offset = opening.get("offset", 0)
            width = opening.get("width", 0)
            height = opening.get("height", 0)
            if width <= 0 or height <= 0:
                errors.append(f"{p}: opening {opening.get('id')} dimensions must be positive")
            if offset < 0 or offset + width > wlen + 1e-6:
                errors.append(f"{p}: opening {opening.get('id')} does not fit host wall")
            if height > wall["geometry"]["height"] + 1e-6:
                errors.append(f"{p}: opening {opening.get('id')} exceeds wall height")
            if collection == "windows" and opening.get("sill_height", 0) < 0:
                errors.append(f"{p}: window {opening.get('id')} sill_height must be >= 0")

    return errors


def _validate_level_rules(output: dict, level: int, p: str) -> list[str]:
    errors: list[str] = []
    elements = output["elements"]
    storeys = output["storeys"]
    structural_count = _count_structural(elements)

    if level >= 2:
        if structural_count < 2:
            errors.append(f"{p}: at least two structural elements required")
        if level < 4 and (elements["doors"] or elements["windows"]):
            errors.append(f"{p}: openings must be empty below level 4")
        if level < 5 and elements["spaces"]:
            errors.append(f"{p}: spaces must be empty below level 5")
        if level < 6 and len(storeys) != 1:
            errors.append(f"{p}: exactly one storey required below level 6")
        if level < 6 and elements["stairs"]:
            errors.append(f"{p}: stairs must be empty below level 6")
        if level < 7 and elements["roofs"]:
            errors.append(f"{p}: roofs must be empty below level 7")
        if level < 8 and output["materials"]:
            errors.append(f"{p}: materials must be empty below level 8")
        if level < 9 and output["relationships"]:
            errors.append(f"{p}: relationships must be empty below level 9")

    if level >= 3 and not _has_geometry_variation(elements):
        errors.append(f"{p}: geometry variation required (diagonal lines or complex outlines)")

    if level >= 4:
        if not elements["doors"] and not elements["windows"]:
            errors.append(f"{p}: at least one opening required")
        errors.extend(_validate_openings(elements, p))

    if level >= 5 and len(elements["spaces"]) < 2:
        errors.append(f"{p}: at least two spaces required")

    if level >= 6:
        if len(storeys) < 2:
            errors.append(f"{p}: at least two storeys required")
        if not elements["stairs"]:
            errors.append(f"{p}: at least one stair required")
        storey_ids = {storey["id"] for storey in storeys}
        for stair in elements["stairs"]:
            if stair.get("from_storey") not in storey_ids or stair.get("to_storey") not in storey_ids:
                errors.append(f"{p}: stair {stair.get('id')} references invalid storeys")

    if level >= 7 and not elements["roofs"]:
        errors.append(f"{p}: at least one roof required")

    if level >= 8:
        material_ids = {material["id"] for material in output["materials"]}
        if not material_ids:
            errors.append(f"{p}: materials definitions required")
        material_collections = (
            "walls",
            "slabs",
            "columns",
            "beams",
            "doors",
            "windows",
            "roofs",
            "stairs",
        )
        for collection in material_collections:
            for element in elements[collection]:
                material_id = element.get("material")
                if not material_id or material_id not in material_ids:
                    errors.append(
                        f"{p}: element {element.get('id')} must reference a defined material"
                    )

    if level >= 9:
        if not output["relationships"]:
            errors.append(f"{p}: relationships required")
        valid_ids = collect_element_ids(output)
        rel_types = {rel.get("type") for rel in output["relationships"]}
        required_types = {"contains", "hosts", "connects", "bounds_space", "assigns_material"}
        missing_types = required_types - rel_types
        if missing_types:
            errors.append(f"{p}: missing relationship types: {sorted(missing_types)}")
        for rel in output["relationships"]:
            if rel.get("from") not in valid_ids or rel.get("to") not in valid_ids:
                errors.append(f"{p}: relationship {rel.get('id')} has invalid endpoints")

    if level >= 10:
        for collection in ELEMENT_COLLECTIONS:
            if not elements[collection]:
                errors.append(f"{p}: level 10 requires populated elements.{collection}")
        if len(output["materials"]) < 5:
            errors.append(f"{p}: level 10 requires comprehensive material definitions")
        if len(output["relationships"]) < 8:
            errors.append(f"{p}: level 10 requires comprehensive relationships")

    return errors


def validate_dataset_file(level: int, path: Path) -> list[str]:
    dataset_name = path.name
    errors: list[str] = []

    if not path.exists():
        return [f"Missing dataset for level {level}: {path}"]

    records: list[dict] = []
    prompts: set[str] = set()

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.append(f"{dataset_name} line {line_number}: invalid JSON ({exc})")
                continue
            records.append(record)
            prompt = record.get("input", "")
            if prompt in prompts:
                errors.append(f"{dataset_name} line {line_number}: duplicate input prompt")
            prompts.add(prompt)
            errors.extend(_validate_base(record, level, line_number, dataset_name))
            errors.extend(_validate_level_rules(record["output"], level, _prefix(level, line_number, dataset_name)))

    if len(records) != RECORDS_PER_LEVEL:
        errors.append(
            f"{dataset_name}: expected {RECORDS_PER_LEVEL} records, found {len(records)}"
        )

    return errors


def validate_all() -> list[str]:
    errors: list[str] = []
    for level, filename in LEVEL_FILES.items():
        path = DATASETS_DIR / filename
        errors.extend(validate_dataset_file(level, path))
    return errors


def main() -> int:
    errors = validate_all()
    if errors:
        print("Levels 2-10 dataset validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    total = len(LEVEL_FILES) * RECORDS_PER_LEVEL
    print(f"Validated levels 2-10 successfully ({total} records).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
