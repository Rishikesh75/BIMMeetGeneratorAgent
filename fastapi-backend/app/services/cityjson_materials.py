"""Deterministically color a generated CityJSON model by element type.

Gemini is asked to tag each CityObject with attributes.element_type (see
doc_to_cityjson.py) but is not trusted to also hand-write the nested
material-index arrays CityJSON requires - getting those right by hand is easy
to get wrong and hard to validate. Coloring is applied here instead, after
geometry generation, the same way the rest of this pipeline prefers fixed
rules over LLM guesses wherever a rule can be stated.
"""

from __future__ import annotations

from typing import Any

# (diffuseColor RGB 0-1, transparency 0-1) per element type.
MATERIAL_STYLES: dict[str, tuple[str, tuple[float, float, float], float]] = {
    "wall": ("Wall - Light Cream", (0.96, 0.91, 0.80), 0.0),
    "slab": ("Slab - Concrete", (0.75, 0.75, 0.75), 0.0),
    "roof": ("Roof - Dark Grey Tile", (0.25, 0.25, 0.25), 0.0),
    "stair": ("Staircase - Light Grey", (0.80, 0.80, 0.80), 0.0),
    "door": ("Door - Brown", (0.40, 0.26, 0.13), 0.0),
    "window": ("Window - Glass", (0.75, 0.88, 0.95), 0.35),
    "column": ("Column - Concrete", (0.75, 0.75, 0.75), 0.0),
    "room": ("Room Volume", (0.90, 0.95, 0.85), 0.75),
    "other": ("Generic Element", (0.70, 0.70, 0.70), 0.0),
}


def _mirror_shape(boundaries: Any, geom_type: str, material_index: int) -> Any:
    """Build a material-index array with the same nesting as `boundaries`.

    Mirrors cityjson_to_ifc.py's iter_surfaces() nesting rules exactly, so the
    produced "material.values" array lines up with however build_face_sets()
    will walk the boundaries, for any geometry type - not just our own boxes.
    """
    gt = (geom_type or "").lower()
    if gt in ("multisurface", "compositesurface"):
        return [material_index for _ in boundaries]
    if gt == "solid":
        return [[material_index for _ in shell] for shell in boundaries]
    if gt in ("multisolid", "compositesolid"):
        return [[[material_index for _ in shell] for shell in solid] for solid in boundaries]
    return [material_index for _ in boundaries]


def apply_materials(cityjson: dict[str, Any]) -> dict[str, Any]:
    """Add appearance.materials and per-geometry material indices, in place."""
    materials: list[dict[str, Any]] = []
    index_by_type: dict[str, int] = {}

    def material_index_for(element_type: str) -> int:
        key = (element_type or "other").strip().lower()
        if key not in MATERIAL_STYLES:
            key = "other"
        if key in index_by_type:
            return index_by_type[key]
        name, rgb, transparency = MATERIAL_STYLES[key]
        materials.append(
            {
                "name": name,
                "diffuseColor": list(rgb),
                "transparency": transparency,
            }
        )
        index = len(materials) - 1
        index_by_type[key] = index
        return index

    templates = cityjson.get("geometry-templates", {}).get("templates", [])

    for city_object in cityjson.get("CityObjects", {}).values():
        if city_object.get("type") == "Building":
            continue
        element_type = city_object.get("attributes", {}).get("element_type", "other")
        material_index = material_index_for(element_type)

        for geometry in city_object.get("geometry", []):
            if geometry.get("type") == "GeometryInstance":
                # The geometry's own "boundaries" is just [anchor_vertex_index], not a face
                # list - the actual face/shell nesting to mirror lives on the referenced
                # template, which is what cityjson_to_ifc.py walks when it resolves the
                # instance's material.values.
                template_idx = geometry.get("template")
                if not isinstance(template_idx, int) or not (0 <= template_idx < len(templates)):
                    continue
                template = templates[template_idx]
                boundaries = template.get("boundaries")
                inner_type = template.get("type", "")
            else:
                boundaries = geometry.get("boundaries")
                inner_type = geometry.get("type", "")
            if boundaries is None:
                continue
            values = _mirror_shape(boundaries, inner_type, material_index)
            geometry["material"] = {"default": {"values": values}}

    if materials:
        cityjson.setdefault("appearance", {})["materials"] = materials
    return cityjson
