"""Shared helpers for hierarchical BIM dataset generation and validation."""

from __future__ import annotations

import math
from typing import Any

ELEMENT_COLLECTIONS = (
    "walls",
    "slabs",
    "columns",
    "beams",
    "doors",
    "windows",
    "roofs",
    "stairs",
    "spaces",
)

REQUIRED_TOP_LEVEL = (
    "project",
    "site",
    "building",
    "storeys",
    "elements",
    "materials",
    "relationships",
    "metadata",
)

LEVEL_FILES: dict[int, str] = {
    2: "level-02-multiple-elements.jsonl",
    3: "level-03-geometry.jsonl",
    4: "level-04-openings.jsonl",
    5: "level-05-multiple-rooms.jsonl",
    6: "level-06-multiple-storeys.jsonl",
    7: "level-07-complex-buildings.jsonl",
    8: "level-08-materials.jsonl",
    9: "level-09-relationships.jsonl",
    10: "level-10-complete-ifc-ready-buildings.jsonl",
}

BUILDING_TYPES = (
    "office",
    "residential",
    "warehouse",
    "school",
    "hospital",
    "retail",
    "industrial",
    "mixed_use",
)

SPACE_USAGES = (
    "office",
    "corridor",
    "meeting",
    "storage",
    "lobby",
    "classroom",
    "bedroom",
    "kitchen",
    "bathroom",
    "retail",
)


def empty_elements() -> dict[str, list]:
    return {name: [] for name in ELEMENT_COLLECTIONS}


def distance(start: list[float], end: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(start, end)))


def outline_area(outline: list[list[float]]) -> float:
    if len(outline) < 3:
        return 0.0
    area = 0.0
    for i, point in enumerate(outline):
        nxt = outline[(i + 1) % len(outline)]
        area += point[0] * nxt[1] - nxt[0] * point[1]
    return abs(area) / 2.0


def rectangular_outline(
    origin_x: float, origin_y: float, width: float, depth: float, z: float = 0.0
) -> list[list[float]]:
    return [
        [origin_x, origin_y, z],
        [origin_x + width, origin_y, z],
        [origin_x + width, origin_y + depth, z],
        [origin_x, origin_y + depth, z],
    ]


def l_shaped_outline(
    origin_x: float, origin_y: float, width: float, depth: float, z: float = 0.0
) -> list[list[float]]:
    notch = min(width, depth) * 0.4
    return [
        [origin_x, origin_y, z],
        [origin_x + width, origin_y, z],
        [origin_x + width, origin_y + depth - notch, z],
        [origin_x + width - notch, origin_y + depth - notch, z],
        [origin_x + width - notch, origin_y + depth, z],
        [origin_x, origin_y + depth, z],
    ]


def make_metadata(level: int, note: str) -> dict[str, Any]:
    return {
        "units": "meters",
        "coordinate_system": "right_handed_z_up",
        "schema_version": "1.0",
        "dataset_level": level,
        "note": note,
    }


def collect_element_ids(output: dict) -> set[str]:
    ids: set[str] = set()
    for key in ("project", "site", "building"):
        item_id = output.get(key, {}).get("id")
        if item_id:
            ids.add(item_id)
    for storey in output.get("storeys", []):
        if storey.get("id"):
            ids.add(storey["id"])
    for material in output.get("materials", []):
        if material.get("id"):
            ids.add(material["id"])
    for relationship in output.get("relationships", []):
        if relationship.get("id"):
            ids.add(relationship["id"])
    for collection in ELEMENT_COLLECTIONS:
        for element in output.get("elements", {}).get(collection, []):
            if element.get("id"):
                ids.add(element["id"])
    return ids


def wall_length(wall: dict) -> float:
    geometry = wall.get("geometry", {})
    start = geometry.get("start", [])
    end = geometry.get("end", [])
    if len(start) == 3 and len(end) == 3:
        return distance(start, end)
    return 0.0
