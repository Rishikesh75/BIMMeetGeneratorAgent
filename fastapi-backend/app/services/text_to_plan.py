from __future__ import annotations

import re

from bim_ifc_builder import BuildingElement, BuildingPlan, Position


def _extract_dimension(pattern: str, text: str, default: float) -> float:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return default
    return float(match.group(1))


def text_to_building_plan(description: str) -> BuildingPlan:
    """Convert natural language into a structured building plan.

    This is a lightweight rules-based stub that will later be replaced by an ML/LLM
    text-to-JSON model. It extracts a few common cues and falls back to defaults.
    """
    cleaned = (description or "Generated BIM model").strip() or "Generated BIM model"
    project_name = cleaned[:80]

    lower = cleaned.lower()
    building_type = "generic"
    if "warehouse" in lower:
        building_type = "warehouse"
    elif "office" in lower:
        building_type = "office"
    elif "house" in lower or "residential" in lower:
        building_type = "residential"

    floors = 2 if re.search(r"\b2[\s-]?story\b|\btwo[\s-]?story\b", lower) else 1

    length = _extract_dimension(r"(\d+(?:\.\d+)?)\s*m(?:etre|eter|eters|res)?\s*(?:long|length)?", lower, 10.0)
    width = _extract_dimension(r"(\d+(?:\.\d+)?)\s*m(?:etre|eter|eters|res)?\s*(?:wide|width)?", lower, 8.0)
    height = _extract_dimension(r"(\d+(?:\.\d+)?)\s*m(?:etre|eter|eters|res)?\s*(?:high|height|tall)?", lower, 3.0)

    elements: list[BuildingElement] = [
        BuildingElement(
            type="slab",
            name="Ground Floor Slab",
            width_m=width,
            depth_m=length,
            thickness_m=0.25,
        ),
        BuildingElement(
            type="wall",
            name="North Wall",
            length_m=width,
            height_m=height,
            thickness_m=0.2,
            position=Position(x=0, y=0, z=0),
        ),
        BuildingElement(
            type="wall",
            name="South Wall",
            length_m=width,
            height_m=height,
            thickness_m=0.2,
            position=Position(x=0, y=length, z=0),
        ),
        BuildingElement(
            type="wall",
            name="East Wall",
            length_m=length,
            height_m=height,
            thickness_m=0.2,
            position=Position(x=width, y=0, z=0),
            rotation_deg=90,
        ),
        BuildingElement(
            type="wall",
            name="West Wall",
            length_m=length,
            height_m=height,
            thickness_m=0.2,
            position=Position(x=0, y=0, z=0),
            rotation_deg=90,
        ),
    ]

    if floors > 1:
        elements.append(
            BuildingElement(
                type="slab",
                name="First Floor Slab",
                floor=2,
                width_m=width,
                depth_m=length,
                thickness_m=0.25,
                position=Position(z=height),
            )
        )

    return BuildingPlan(
        name=project_name,
        building_type=building_type,
        floors=floors,
        elements=elements,
    )
