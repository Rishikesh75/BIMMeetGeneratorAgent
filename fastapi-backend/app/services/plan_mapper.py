"""Map hierarchical BIM JSON onto the flat BuildingPlan the IFC builder accepts."""

from __future__ import annotations

import math
from typing import Any

from bim_ifc_builder import BuildingElement, BuildingPlan, Position

class PlanMappingError(ValueError):
    """Raised when model JSON has no walls or slabs the IFC builder can place."""


def hierarchical_to_building_plan(plan: dict[str, Any], fallback_name: str) -> BuildingPlan:
    """Convert walls and slabs into BuildingPlan elements.

    Columns, beams, doors, windows, roofs, stairs, and spaces are skipped.
    The current IFC builder only creates wall and slab geometry.
    """
    elements_block = plan.get("elements")
    if not isinstance(elements_block, dict):
        raise PlanMappingError("Model JSON has no elements object to map")

    storey_floors, storey_count = _storey_floors(plan)
    elements: list[BuildingElement] = []
    elements.extend(_map_collection(elements_block.get("walls"), _wall_element, storey_floors))
    elements.extend(_map_collection(elements_block.get("slabs"), _slab_element, storey_floors))
    if not elements:
        raise PlanMappingError("Model JSON had no mappable walls or slabs")

    floor_count = max([storey_count, *(element.floor for element in elements), 1])
    return BuildingPlan(
        name=_building_name(plan, fallback_name),
        building_type="generic",
        floors=floor_count,
        elements=elements,
    )


def _map_collection(items: Any, mapper, storey_floors: dict[str, int]) -> list[BuildingElement]:
    if not isinstance(items, list):
        return []
    mapped: list[BuildingElement] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        element = mapper(item, storey_floors)
        if element is not None:
            mapped.append(element)
    return mapped


def _wall_element(wall: dict[str, Any], storey_floors: dict[str, int]) -> BuildingElement | None:
    geometry = wall.get("geometry")
    if not isinstance(geometry, dict):
        return None
    start = _point(geometry.get("start"))
    end = _point(geometry.get("end"))
    if start is None or end is None:
        return None

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return None

    return BuildingElement(
        type="wall",
        name=_element_name(wall, "Wall"),
        floor=_floor_for(wall.get("storey"), storey_floors),
        length_m=length,
        height_m=_optional_float(geometry.get("height")),
        thickness_m=_optional_float(geometry.get("thickness")),
        position=Position(x=start[0], y=start[1], z=start[2]),
        rotation_deg=math.degrees(math.atan2(dy, dx)),
    )


def _slab_element(slab: dict[str, Any], storey_floors: dict[str, int]) -> BuildingElement | None:
    outline = slab.get("outline")
    if not isinstance(outline, list):
        return None
    points = [point for point in (_point(item) for item in outline) if point is not None]
    if len(points) < 2:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    width = max(xs) - min(xs)
    depth = max(ys) - min(ys)
    if width < 1e-6 or depth < 1e-6:
        return None

    return BuildingElement(
        type="slab",
        name=_element_name(slab, "Slab"),
        floor=_floor_for(slab.get("storey"), storey_floors),
        width_m=width,
        depth_m=depth,
        thickness_m=_optional_float(slab.get("thickness")),
        position=Position(x=min(xs), y=min(ys), z=min(zs)),
    )


def _storey_floors(plan: dict[str, Any]) -> tuple[dict[str, int], int]:
    storeys = plan.get("storeys")
    mapping: dict[str, int] = {}
    if not isinstance(storeys, list):
        return mapping, 0
    for index, storey in enumerate(storeys, start=1):
        if isinstance(storey, dict) and storey.get("id") not in (None, ""):
            mapping[str(storey["id"])] = index
    return mapping, len(storeys)


def _floor_for(storey_id: Any, storey_floors: dict[str, int]) -> int:
    if storey_id is None:
        return 1
    key = str(storey_id)
    if key in storey_floors:
        return storey_floors[key]
    try:
        parsed = int(key)
    except ValueError:
        return 1
    return parsed if parsed >= 1 else 1


def _building_name(plan: dict[str, Any], fallback_name: str) -> str:
    for container_key in ("project", "building"):
        container = plan.get(container_key)
        if not isinstance(container, dict):
            continue
        name = container.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()[:80]
    cleaned = (fallback_name or "Generated BIM model").strip() or "Generated BIM model"
    return cleaned[:80]


def _element_name(item: dict[str, Any], fallback: str) -> str:
    name = item.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    item_id = item.get("id")
    if isinstance(item_id, str) and item_id.strip():
        return item_id.strip()
    return fallback


def _point(value: Any) -> tuple[float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        x = float(value[0])
        y = float(value[1])
        z = float(value[2]) if len(value) > 2 and value[2] is not None else 0.0
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(number) for number in (x, y, z)):
        return None
    return x, y, z


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number
