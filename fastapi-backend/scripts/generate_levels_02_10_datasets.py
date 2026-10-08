"""Generate cumulative BIM datasets for Levels 2 through 10."""

from __future__ import annotations

import json
from pathlib import Path

from dataset_common import (
    BUILDING_TYPES,
    ELEMENT_COLLECTIONS,
    LEVEL_FILES,
    SPACE_USAGES,
    distance,
    empty_elements,
    l_shaped_outline,
    make_metadata,
    rectangular_outline,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASETS_DIR = REPO_ROOT / "datasets"
RECORDS_PER_LEVEL = 50


def _idx(level: int, index: int) -> str:
    return f"L{level:02d}-{index:03d}"


def _dims(index: int) -> dict[str, float]:
    width = 8.0 + (index % 6) * 1.5
    depth = 10.0 + (index % 5) * 1.2
    height = 2.8 + (index % 4) * 0.35
    return {
        "width": round(width, 2),
        "depth": round(depth, 2),
        "height": round(height, 2),
        "thickness": round(0.15 + (index % 5) * 0.03, 2),
        "slab_thickness": round(0.2 + (index % 3) * 0.05, 2),
        "column_size": round(0.35 + (index % 4) * 0.05, 2),
        "beam_depth": round(0.4 + (index % 3) * 0.08, 2),
    }


def _storey_count(level: int, index: int) -> int:
    if level < 6:
        return 1
    return 2 + (index % 3)


def _build_storeys(level: int, index: int, dims: dict[str, float]) -> list[dict]:
    count = _storey_count(level, index)
    storeys: list[dict] = []
    elevation = 0.0
    for storey_index in range(count):
        storey_id = f"storey-{_idx(level, index)}-{storey_index + 1}"
        name = "Ground Floor" if storey_index == 0 else f"Level {storey_index + 1}"
        storeys.append(
            {
                "id": storey_id,
                "name": name,
                "elevation": round(elevation, 2),
                "height": dims["height"],
            }
        )
        elevation += dims["height"]
    return storeys


def _wall(
    wall_id: str,
    name: str,
    storey_id: str,
    material: str,
    start: list[float],
    end: list[float],
    height: float,
    thickness: float,
) -> dict:
    return {
        "id": wall_id,
        "name": name,
        "storey": storey_id,
        "material": material,
        "geometry": {
            "start": start,
            "end": end,
            "height": height,
            "thickness": thickness,
        },
    }


def _slab(
    slab_id: str,
    name: str,
    storey_id: str,
    material: str,
    outline: list[list[float]],
    thickness: float,
) -> dict:
    return {
        "id": slab_id,
        "name": name,
        "storey": storey_id,
        "material": material,
        "outline": outline,
        "thickness": thickness,
    }


def _column(
    column_id: str,
    name: str,
    storey_id: str,
    material: str,
    position: list[float],
    width: float,
    depth: float,
    height: float,
) -> dict:
    return {
        "id": column_id,
        "name": name,
        "storey": storey_id,
        "material": material,
        "position": position,
        "width": width,
        "depth": depth,
        "height": height,
    }


def _beam(
    beam_id: str,
    name: str,
    storey_id: str,
    material: str,
    start: list[float],
    end: list[float],
    width: float,
    height: float,
) -> dict:
    return {
        "id": beam_id,
        "name": name,
        "storey": storey_id,
        "material": material,
        "start": start,
        "end": end,
        "width": width,
        "height": height,
    }


def _door(
    door_id: str,
    name: str,
    storey_id: str,
    host_wall: str,
    material: str,
    width: float,
    height: float,
    offset: float,
    sill_height: float = 0.0,
) -> dict:
    return {
        "id": door_id,
        "name": name,
        "storey": storey_id,
        "host_wall": host_wall,
        "material": material,
        "width": width,
        "height": height,
        "offset": offset,
        "sill_height": sill_height,
    }


def _window(
    window_id: str,
    name: str,
    storey_id: str,
    host_wall: str,
    material: str,
    width: float,
    height: float,
    offset: float,
    sill_height: float,
) -> dict:
    return {
        "id": window_id,
        "name": name,
        "storey": storey_id,
        "host_wall": host_wall,
        "material": material,
        "width": width,
        "height": height,
        "offset": offset,
        "sill_height": sill_height,
    }


def _roof(
    roof_id: str,
    name: str,
    storey_id: str,
    material: str,
    outline: list[list[float]],
    thickness: float,
    slope_deg: float,
) -> dict:
    return {
        "id": roof_id,
        "name": name,
        "storey": storey_id,
        "material": material,
        "outline": outline,
        "thickness": thickness,
        "slope_deg": slope_deg,
    }


def _stair(
    stair_id: str,
    name: str,
    from_storey: str,
    to_storey: str,
    material: str,
    start: list[float],
    end: list[float],
    width: float,
    riser_height: float,
    tread_depth: float,
) -> dict:
    return {
        "id": stair_id,
        "name": name,
        "from_storey": from_storey,
        "to_storey": to_storey,
        "material": material,
        "geometry": {
            "start": start,
            "end": end,
            "width": width,
            "riser_height": riser_height,
            "tread_depth": tread_depth,
        },
    }


def _space(
    space_id: str,
    name: str,
    storey_id: str,
    usage: str,
    outline: list[list[float]],
    height: float,
) -> dict:
    return {
        "id": space_id,
        "name": name,
        "storey": storey_id,
        "usage": usage,
        "outline": outline,
        "height": height,
    }


def _material(
    material_id: str,
    name: str,
    category: str,
    density: float,
    color: str,
) -> dict:
    return {
        "id": material_id,
        "name": name,
        "category": category,
        "density_kg_m3": density,
        "color": color,
    }


def _relationship(rel_id: str, rel_type: str, from_id: str, to_id: str) -> dict:
    return {"id": rel_id, "type": rel_type, "from": from_id, "to": to_id}


def _material_ids(level: int, index: int) -> dict[str, str]:
    prefix = _idx(level, index)
    return {
        "concrete": f"mat-concrete-{prefix}",
        "steel": f"mat-steel-{prefix}",
        "timber": f"mat-timber-{prefix}",
        "glass": f"mat-glass-{prefix}",
        "insulation": f"mat-insulation-{prefix}",
        "door": f"mat-door-{prefix}",
        "window": f"mat-window-{prefix}",
        "roof": f"mat-roof-{prefix}",
    }


def _build_materials(level: int, index: int) -> list[dict]:
    if level < 8:
        return []
    mats = _material_ids(level, index)
    return [
        _material(mats["concrete"], "Structural Concrete C30", "concrete", 2400, "#B0B0B0"),
        _material(mats["steel"], "Structural Steel S355", "steel", 7850, "#708090"),
        _material(mats["timber"], "Engineered Timber GL24", "timber", 450, "#C19A6B"),
        _material(mats["glass"], "Double Glazed Glass", "glass", 2500, "#87CEEB"),
        _material(mats["insulation"], "Mineral Wool Insulation", "insulation", 40, "#F5DEB3"),
        _material(mats["door"], "Solid Core Door Panel", "wood", 650, "#8B4513"),
        _material(mats["window"], "Aluminum Window Frame", "metal", 2700, "#C0C0C0"),
        _material(mats["roof"], "Membrane Roofing", "membrane", 1200, "#696969"),
    ]


def _rect_walls(
    level: int,
    index: int,
    storey_id: str,
    dims: dict[str, float],
    material: str,
    diagonal: bool = False,
    id_suffix: str = "",
) -> list[dict]:
    width = dims["width"]
    depth = dims["depth"]
    height = dims["height"]
    thickness = dims["thickness"]
    prefix = _idx(level, index)
    suffix = f"-{id_suffix}" if id_suffix else ""

    north = _wall(
        f"wall-n-{prefix}{suffix}",
        "North Wall",
        storey_id,
        material,
        [0.0, 0.0, 0.0],
        [width, 0.0, 0.0],
        height,
        thickness,
    )
    south = _wall(
        f"wall-s-{prefix}{suffix}",
        "South Wall",
        storey_id,
        material,
        [0.0, depth, 0.0],
        [width, depth, 0.0],
        height,
        thickness,
    )
    east = _wall(
        f"wall-e-{prefix}{suffix}",
        "East Wall",
        storey_id,
        material,
        [width, 0.0, 0.0],
        [width, depth, 0.0],
        height,
        thickness,
    )
    west = _wall(
        f"wall-w-{prefix}{suffix}",
        "West Wall",
        storey_id,
        material,
        [0.0, 0.0, 0.0],
        [0.0, depth, 0.0],
        height,
        thickness,
    )

    walls = [north, south, east, west]
    if diagonal and level >= 3:
        walls.append(
            _wall(
                f"wall-d-{prefix}{suffix}",
                "Diagonal Feature Wall",
                storey_id,
                material,
                [1.0, 1.0, 0.0],
                [width * 0.55, depth * 0.45, 0.0],
                height,
                thickness,
            )
        )
    return walls


def _build_elements(
    level: int,
    index: int,
    storeys: list[dict],
    dims: dict[str, float],
) -> dict[str, list]:
    elements = empty_elements()
    prefix = _idx(level, index)
    mats = _material_ids(level, index)
    mat_concrete = mats["concrete"] if level >= 8 else ""
    mat_steel = mats["steel"] if level >= 8 else ""
    mat_timber = mats["timber"] if level >= 8 else ""
    mat_glass = mats["glass"] if level >= 8 else ""
    mat_door = mats["door"] if level >= 8 else ""
    mat_window = mats["window"] if level >= 8 else ""
    mat_roof = mats["roof"] if level >= 8 else ""

    ground = storeys[0]["id"]
    upper = storeys[1]["id"] if len(storeys) > 1 else ground
    width = dims["width"]
    depth = dims["depth"]
    height = dims["height"]
    diagonal = level >= 3 or index % 3 == 0

    # Level 2+: structural elements
    walls = _rect_walls(level, index, ground, dims, mat_concrete, diagonal=diagonal)
    elements["walls"] = walls[:2] if level == 2 and index % 2 == 0 else walls

    elements["slabs"].append(
        _slab(
            f"slab-gf-{prefix}",
            "Ground Floor Slab",
            ground,
            mat_concrete,
            rectangular_outline(0.0, 0.0, width, depth),
            dims["slab_thickness"],
        )
    )

    if level >= 2 and (index % 2 == 1 or level >= 3):
        elements["columns"].append(
            _column(
                f"column-c1-{prefix}",
                "Corner Column C1",
                ground,
                mat_concrete,
                [0.5, 0.5, 0.0],
                dims["column_size"],
                dims["column_size"],
                height,
            )
        )

    if level >= 2 and (index % 3 == 0 or level >= 3):
        elements["beams"].append(
            _beam(
                f"beam-b1-{prefix}",
                "Main Beam B1",
                ground,
                mat_steel,
                [0.5, 0.5, height - dims["beam_depth"]],
                [width - 0.5, 0.5, height - dims["beam_depth"]],
                dims["column_size"],
                dims["beam_depth"],
            )
        )

    # Level 3+: richer geometry
    if level >= 3 and index % 4 == 0:
        elements["slabs"].append(
            _slab(
                f"slab-mezz-{prefix}",
                "Mezzanine Slab",
                ground,
                mat_concrete,
                l_shaped_outline(1.0, 1.0, width * 0.6, depth * 0.5),
                dims["slab_thickness"],
            )
        )

    if level >= 3 and index % 5 == 0:
        elements["beams"].append(
            _beam(
                f"beam-diag-{prefix}",
                "Diagonal Transfer Beam",
                ground,
                mat_steel,
                [1.0, 1.0, height - dims["beam_depth"]],
                [width - 1.0, depth - 1.0, height - dims["beam_depth"]],
                dims["column_size"],
                dims["beam_depth"],
            )
        )

    # Level 4+: openings
    if level >= 4:
        host_wall = elements["walls"][0]["id"]
        wall_len = distance(
            elements["walls"][0]["geometry"]["start"],
            elements["walls"][0]["geometry"]["end"],
        )
        door_width = min(1.0, wall_len * 0.2)
        window_width = min(1.5, wall_len * 0.25)
        elements["doors"].append(
            _door(
                f"door-main-{prefix}",
                "Main Entrance Door",
                ground,
                host_wall,
                mat_door,
                door_width,
                min(2.1, height - 0.1),
                1.0,
            )
        )
        if index % 2 == 0:
            elements["windows"].append(
                _window(
                    f"window-n1-{prefix}",
                    "North Window 1",
                    ground,
                    host_wall,
                    mat_window,
                    window_width,
                    1.2,
                    wall_len * 0.35,
                    1.0,
                )
            )
        if index % 3 == 0:
            side_wall = elements["walls"][2]["id"] if len(elements["walls"]) > 2 else host_wall
            side_len = wall_length_by_id(elements["walls"], side_wall)
            elements["windows"].append(
                _window(
                    f"window-e1-{prefix}",
                    "East Window 1",
                    ground,
                    side_wall,
                    mat_glass if level >= 8 else "",
                    min(1.2, side_len * 0.2),
                    1.0,
                    max(1.0, side_len * 0.3),
                    1.1,
                )
            )

    # Level 5+: multiple rooms
    if level >= 5:
        split_x = width * 0.45
        elements["spaces"].append(
            _space(
                f"space-office-{prefix}",
                "Office Room",
                ground,
                SPACE_USAGES[index % len(SPACE_USAGES)],
                rectangular_outline(0.5, 0.5, split_x - 0.5, depth - 1.0),
                height,
            )
        )
        elements["spaces"].append(
            _space(
                f"space-corridor-{prefix}",
                "Corridor",
                ground,
                "corridor",
                rectangular_outline(split_x, 0.5, width - split_x - 0.5, depth - 1.0),
                height,
            )
        )
        if index % 4 == 0:
            elements["spaces"].append(
                _space(
                    f"space-storage-{prefix}",
                    "Storage Room",
                    ground,
                    "storage",
                    rectangular_outline(1.0, 1.0, width * 0.3, depth * 0.3),
                    height,
                )
            )

    # Level 6+: multiple storeys and stairs
    if level >= 6 and len(storeys) > 1:
        for storey_index, storey in enumerate(storeys[1:], start=1):
            sid = storey["id"]
            elements["slabs"].append(
                _slab(
                    f"slab-l{storey_index + 1}-{prefix}",
                    f"{storey['name']} Slab",
                    sid,
                    mat_concrete,
                    rectangular_outline(0.0, 0.0, width, depth),
                    dims["slab_thickness"],
                )
            )
            elements["walls"].extend(
                _rect_walls(
                    level,
                    index,
                    sid,
                    dims,
                    mat_concrete,
                    diagonal=False,
                    id_suffix=f"s{storey_index + 1}",
                )[:2]
            )
            if level >= 5:
                elements["spaces"].append(
                    _space(
                        f"space-upper-{storey_index}-{prefix}",
                        f"{storey['name']} Open Office",
                        sid,
                        "office",
                        rectangular_outline(1.0, 1.0, width - 2.0, depth - 2.0),
                        height,
                    )
                )

        for i in range(len(storeys) - 1):
            elements["stairs"].append(
                _stair(
                    f"stair-{i + 1}-{prefix}",
                    f"Stair {i + 1}",
                    storeys[i]["id"],
                    storeys[i + 1]["id"],
                    mat_concrete,
                    [width - 2.0, 1.0, 0.0],
                    [width - 1.2, depth - 2.0, 0.0],
                    1.2,
                    round(dims["height"] / 16, 3),
                    0.28,
                )
            )

    # Level 7+: complex buildings with roofs and extra elements
    if level >= 7:
        top_storey = storeys[-1]["id"]
        elements["roofs"].append(
            _roof(
                f"roof-main-{prefix}",
                "Main Roof",
                top_storey,
                mat_roof,
                rectangular_outline(0.0, 0.0, width, depth),
                0.25,
                round(5.0 + (index % 6), 1),
            )
        )
        if index % 2 == 0:
            elements["columns"].append(
                _column(
                    f"column-c2-{prefix}",
                    "Perimeter Column C2",
                    ground,
                    mat_concrete,
                    [width - 0.5, depth - 0.5, 0.0],
                    dims["column_size"],
                    dims["column_size"],
                    height * len(storeys),
                )
            )
        if index % 3 == 0:
            elements["beams"].append(
                _beam(
                    f"beam-perim-{prefix}",
                    "Perimeter Beam",
                    ground,
                    mat_steel,
                    [0.5, depth - 0.5, height - dims["beam_depth"]],
                    [width - 0.5, depth - 0.5, height - dims["beam_depth"]],
                    dims["column_size"],
                    dims["beam_depth"],
                )
            )

    # Level 10: ensure all collections populated
    if level >= 10:
        if not elements["columns"]:
            elements["columns"].append(
                _column(
                    f"column-c3-{prefix}",
                    "Core Column C3",
                    ground,
                    mat_concrete,
                    [width / 2, depth / 2, 0.0],
                    dims["column_size"],
                    dims["column_size"],
                    height,
                )
            )
        if not elements["beams"]:
            elements["beams"].append(
                _beam(
                    f"beam-core-{prefix}",
                    "Core Beam",
                    ground,
                    mat_steel,
                    [1.0, depth / 2, height - dims["beam_depth"]],
                    [width - 1.0, depth / 2, height - dims["beam_depth"]],
                    dims["column_size"],
                    dims["beam_depth"],
                )
            )
        if not elements["doors"]:
            host = elements["walls"][0]["id"]
            elements["doors"].append(
                _door(
                    f"door-secondary-{prefix}",
                    "Secondary Door",
                    ground,
                    host,
                    mat_door,
                    0.9,
                    2.0,
                    2.0,
                )
            )
        if not elements["windows"]:
            host = elements["walls"][1]["id"]
            wlen = wall_length_by_id(elements["walls"], host)
            elements["windows"].append(
                _window(
                    f"window-secondary-{prefix}",
                    "Secondary Window",
                    ground,
                    host,
                    mat_window,
                    1.0,
                    1.0,
                    max(0.5, wlen * 0.4),
                    1.0,
                )
            )
        if not elements["stairs"] and len(storeys) > 1:
            elements["stairs"].append(
                _stair(
                    f"stair-core-{prefix}",
                    "Core Stair",
                    storeys[0]["id"],
                    storeys[1]["id"],
                    mat_concrete,
                    [1.0, 1.0, 0.0],
                    [2.5, depth - 1.5, 0.0],
                    1.1,
                    round(dims["height"] / 14, 3),
                    0.27,
                )
            )
        if len(elements["spaces"]) < 2:
            elements["spaces"].append(
                _space(
                    f"space-utility-{prefix}",
                    "Utility Room",
                    ground,
                    "storage",
                    rectangular_outline(2.0, 2.0, 2.5, 2.5),
                    height,
                )
            )

    return elements


def wall_length_by_id(walls: list[dict], wall_id: str) -> float:
    for wall in walls:
        if wall["id"] == wall_id:
            return distance(wall["geometry"]["start"], wall["geometry"]["end"])
    return 0.0


def _build_relationships(
    level: int,
    index: int,
    output: dict,
) -> list[dict]:
    if level < 9:
        return []

    prefix = _idx(level, index)
    relationships: list[dict] = []
    building_id = output["building"]["id"]
    storeys = output["storeys"]
    elements = output["elements"]
    materials = output["materials"]

    rel_index = 1

    def add(rel_type: str, from_id: str, to_id: str) -> None:
        nonlocal rel_index
        relationships.append(
            _relationship(f"rel-{rel_index:02d}-{prefix}", rel_type, from_id, to_id)
        )
        rel_index += 1

    for storey in storeys:
        add("contains", building_id, storey["id"])

    for collection in ELEMENT_COLLECTIONS:
        for element in elements[collection]:
            storey_ref = element.get("storey") or element.get("from_storey")
            if storey_ref:
                add("contains", storey_ref, element["id"])

    for door in elements["doors"]:
        add("hosts", door["host_wall"], door["id"])
    for window in elements["windows"]:
        add("hosts", window["host_wall"], window["id"])

    if elements["columns"] and elements["beams"]:
        add("connects", elements["columns"][0]["id"], elements["beams"][0]["id"])

    if elements["walls"] and elements["spaces"]:
        add("bounds_space", elements["walls"][0]["id"], elements["spaces"][0]["id"])

    if level >= 9 and materials:
        for collection in ("walls", "slabs", "columns", "beams", "doors", "windows", "roofs", "stairs"):
            for element in elements[collection]:
                material_id = element.get("material")
                if material_id:
                    add("assigns_material", material_id, element["id"])

    if level >= 10:
        for stair in elements["stairs"]:
            add("connects", stair["from_storey"], stair["to_storey"])
        if len(elements["spaces"]) > 1:
            add("bounds_space", elements["walls"][1]["id"], elements["spaces"][1]["id"])

    return relationships


def _build_prompt(level: int, index: int, output: dict, building_type: str) -> str:
    elements = output["elements"]
    storeys = output["storeys"]
    counts = {name: len(elements[name]) for name in ELEMENT_COLLECTIONS}
    parts = [
        f"Design a {building_type.replace('_', ' ')} building",
        f"with {len(storeys)} storey(s)",
    ]

    structural = []
    if counts["walls"]:
        structural.append(f"{counts['walls']} wall(s)")
    if counts["slabs"]:
        structural.append(f"{counts['slabs']} slab(s)")
    if counts["columns"]:
        structural.append(f"{counts['columns']} column(s)")
    if counts["beams"]:
        structural.append(f"{counts['beams']} beam(s)")
    if structural:
        parts.append("including " + ", ".join(structural))

    if level >= 3 and counts["walls"] > 4:
        parts.append("with diagonal wall geometry and non-rectangular slab outlines where applicable")

    openings = []
    if counts["doors"]:
        openings.append(f"{counts['doors']} door(s)")
    if counts["windows"]:
        openings.append(f"{counts['windows']} window(s)")
    if level >= 4 and openings:
        parts.append("Add " + " and ".join(openings) + " hosted on valid walls")

    if level >= 5 and counts["spaces"]:
        parts.append(f"Define {counts['spaces']} room spaces with usage labels and outlines")

    if level >= 6 and len(storeys) > 1:
        parts.append(f"Include {counts['stairs']} stair(s) linking adjacent storeys")

    if level >= 7 and counts["roofs"]:
        parts.append("Include roof geometry with slope and thickness")

    if level >= 8:
        parts.append("Assign material definitions and reference them from all elements")

    if level >= 9:
        parts.append("Add relationship records for containment, hosting, connection, space boundaries, and material assignment")

    if level >= 10:
        parts.append("Return a complete IFC-ready hierarchical building model with consistent IDs and references")

    parts.append(f"Use meters and right-handed Z-up coordinates (example {index}).")
    return ". ".join(parts) + "."


def build_record(level: int, index: int) -> dict:
    dims = _dims(index)
    building_type = BUILDING_TYPES[index % len(BUILDING_TYPES)]
    prefix = _idx(level, index)
    storeys = _build_storeys(level, index, dims)
    materials = _build_materials(level, index)

    output: dict = {
        "project": {
            "id": f"proj-{prefix}",
            "name": f"{building_type.title()} Project {index}",
            "description": f"Level {level} cumulative BIM training example {index}",
        },
        "site": {
            "id": f"site-{prefix}",
            "name": f"Site {index}",
            "location": f"Plot {index % 20 + 1}, District {(index % 7) + 1}",
            "latitude": round(40.0 + index * 0.01, 4) if index % 5 == 0 else None,
            "longitude": round(-74.0 - index * 0.01, 4) if index % 5 == 0 else None,
        },
        "building": {
            "id": f"bld-{prefix}",
            "name": f"{building_type.title()} Building {index}",
            "storeys": [storey["id"] for storey in storeys],
        },
        "storeys": storeys,
        "elements": _build_elements(level, index, storeys, dims),
        "materials": materials,
        "relationships": [],
        "metadata": make_metadata(
            level,
            f"Level {level} cumulative BIM training example.",
        ),
    }

    output["relationships"] = _build_relationships(level, index, output)
    prompt = _build_prompt(level, index, output, building_type)
    return {"input": prompt, "output": output}


def generate_level(level: int) -> Path:
    output_path = DATASETS_DIR / LEVEL_FILES[level]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for index in range(1, RECORDS_PER_LEVEL + 1):
            record = build_record(level, index)
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return output_path


def main() -> None:
    generated: list[str] = []
    for level in range(2, 11):
        path = generate_level(level)
        generated.append(str(path))
        print(f"Wrote level {level} -> {path}")

    print(f"Generated {len(generated)} dataset files ({RECORDS_PER_LEVEL} records each).")


if __name__ == "__main__":
    main()
