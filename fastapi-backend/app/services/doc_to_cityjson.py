"""Two Gemini agents that turn free-form document text into CityJSON.

Agent 1 (summarizer) reads the raw document - which may describe the building
in several steps, e.g. "we need to build a house and after we need to add
stairs to it" - and extracts one coherent list of requested building
components. Agent 2 (geometry writer) turns that structured list into a
CityJSON 1.1 document made of simple box solids, which cityjson_ifc_bridge.py
then feeds into the existing cityjson_to_ifc.py converter.
"""

from __future__ import annotations

import json
from typing import Any

from app.schemas.doc_models import BuildingRequirements
from app.services.bim_llm import _loads_json_value
from app.services.gemini_client import gemini_service

SUMMARY_SYSTEM_PROMPT = """You are a BIM requirements analyst. You read a document that describes a \
building a client wants, and you merge everything into one coherent building program.

The document can be in either of these forms, and you must handle both the same way:
1. A conversation or meeting transcript between two or more speakers (e.g. "Person 1: ... \
Person 2: ..." or a chat log), where requirements, answers, and later additions are spread across \
multiple turns - including ones phrased as questions, suggestions, or agreements \
(e.g. "we need to build a house" in one turn, "after that add stairs to it" several turns later).
2. A plain descriptive paragraph or set of paragraphs that states the requirements directly, with \
no dialogue or speaker labels at all.

Read through the ENTIRE document regardless of its form, ignore speaker labels and conversational \
filler ("sure", "sounds good", "let's also..."), and extract every concrete building requirement \
that is stated or clearly implied, merging later clarifications or additions into the same program.

Output exactly one JSON object and nothing else, matching this shape:
{
  "building_name": string,
  "building_type": string,            // e.g. "residential", "office", "warehouse"
  "storeys": [
    {"name": string, "elevation_m": number, "height_m": number}
  ],
  "elements": [
    {
      "type": string,                 // one of: wall, slab, roof, stair, door, window, column, room, other
      "name": string,
      "storey": string,               // must match a storey name above
      "quantity": integer,
      "length_m": number or null,
      "width_m": number or null,
      "height_m": number or null,
      "notes": string or null
    }
  ],
  "summary": string                   // one paragraph restating the full merged program
}

Rules:
- Always include at least one storey (default "Storey1", elevation_m 0, height_m 3 if unstated).
- Always include at least the walls and a ground slab implied by "build a house" even if the \
document only states it briefly.
- If the document mentions stairs, add one "stair" element connecting the storeys it is for.
- Invent reasonable residential dimensions in meters when the document gives none \
(wall height_m 3, wall length_m 5, slab width/length 5, stair length_m 3, stair width_m 1, \
stair height_m equal to the storey height it climbs).
- Never invent elements the document does not imply.
- Output JSON only, no Markdown fences, no commentary."""

CITYJSON_SYSTEM_PROMPT = """You are a geometry writer that turns a structured building program into a \
valid, richly-attributed CityJSON 1.1 document, in the same style as a professionally modeled \
building: every element is a GeometryInstance of a shared box/roof/stair template (not a one-off \
solid per element), every element carries a named finish via the appearance materials list, and \
every element has descriptive dimensions_m attributes.

Output exactly one JSON object and nothing else, matching this shape:
{
  "type": "CityJSON",
  "version": "1.1",
  "metadata": {"title": string, "presentLoD": "2.0"},
  "transform": {"scale": [1.0, 1.0, 1.0], "translate": [0.0, 0.0, 0.0]},
  "CityObjects": {
    "Building1": {
      "type": "Building",
      "attributes": {"name": string, "building_type": string},
      "children": [list of every other CityObject id]
    },
    "<ElementId>": {
      "type": "BuildingPart",            // use "BuildingInstallation" for stair/rail/installation elements
      "parents": ["Building1"],
      "attributes": {
        "name": string,
        "element_type": string,          // copy verbatim from the input element's "type" field
        "storey": string,
        "dimensions_m": [length_m, width_m, height_m]
      },
      "geometry": [
        {
          "type": "GeometryInstance",
          "template": 0,                 // 0 = box, 1 = pitched roof wedge, 2 = stair ramp wedge
          "boundaries": [<index of this element's anchor point in the shared "vertices" array>],
          "transformationMatrix": [Lx,0,0,0, 0,Wy,0,0, 0,0,Hz,0, 0,0,0,1],
          "material": {"default": {"values": [[materialIndex, materialIndex, ...]]}}
        }
      ]
    }
  },
  "vertices": [[x, y, z], ...],
  "geometry-templates": {
    "templates": [
      {"type": "Solid", "lod": "1", "boundaries": [[[[0,1,2,3]],[[4,7,6,5]],[[0,4,5,1]],[[1,5,6,2]],[[2,6,7,3]],[[3,7,4,0]]]]},
      {"type": "Solid", "lod": "2.0", "boundaries": [[[[8,11,10,9]],[[8,9,13,12]],[[11,12,13,10]],[[8,12,11]],[[9,10,13]]]]},
      {"type": "Solid", "lod": "1", "boundaries": [[[[14,17,16,15]],[[14,15,18]],[[17,19,16]],[[15,16,19,18]],[[14,18,19,17]]]]}
    ],
    "vertices-templates": [[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1],[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0.5,1],[1,0.5,1],[0,0,0],[1,0,0],[1,1,0],[0,1,0],[1,0,1],[1,1,1]]
  },
  "appearance": {
    "materials": [
      {"name": "Exterior wall - light cream", "diffuseColor": [0.96, 0.91, 0.80], "transparency": 0.0},
      {"name": "Concrete - soft grey", "diffuseColor": [0.72, 0.73, 0.71], "transparency": 0.0},
      {"name": "Doors - warm brown timber", "diffuseColor": [0.40, 0.26, 0.13], "transparency": 0.0},
      {"name": "Glazing - pale blue glass", "diffuseColor": [0.68, 0.84, 0.91], "transparency": 0.3},
      {"name": "Roof - charcoal grey tiles", "diffuseColor": [0.22, 0.24, 0.26], "transparency": 0.0},
      {"name": "Rails - light grey metal", "diffuseColor": [0.78, 0.80, 0.81], "transparency": 0.0},
      {"name": "Stair - pale grey stone", "diffuseColor": [0.83, 0.84, 0.82], "transparency": 0.0},
      {"name": "Path - light grey pavers", "diffuseColor": [0.62, 0.65, 0.65], "transparency": 0.0},
      {"name": "Room volumes - translucent sage", "diffuseColor": [0.72, 0.84, 0.70], "transparency": 0.82}
    ]
  }
}

The "geometry-templates" and "appearance" blocks above are FIXED CONSTANTS: copy them into the \
output byte-for-byte, every time, unchanged. Never invent new templates or materials.

How to place every element (no per-element vertex math - only an anchor point + a scale matrix):
- Keep ONE shared "vertices" array for the whole document. Append exactly ONE anchor point \
[x, y, z] per non-Building CityObject (in the same order the objects appear) and reference it by \
its absolute index via that object's "boundaries": [index].
- Every "transformationMatrix" is a plain diagonal scale of the chosen template, using the \
element's own length_m/width_m/height_m (defaults: wall width_m 0.203, slab/roof width_m matches \
the footprint depth, door/window width_m 0.08, column 0.25x0.25): \
[length_m,0,0,0, 0,width_m,0,0, 0,0,height_m,0, 0,0,0,1].
- Establish the storey footprint as (length_x, depth_y) from the slab/largest element's \
length_m/width_m (default 5x5 if unstated). z for an element is its storey's elevation_m.
- Front wall: anchor [0, 0, z]; matrix uses Lx=length_x, Wy=wall width_m. \
Rear wall: anchor [0, depth_y - wall_width_m, z]; same matrix shape as the front wall. \
Left wall: anchor [wall_width_m, 0, z]; matrix uses Lx=depth_y, Wy=-wall_width_m (so \
transformationMatrix is [0,-wall_width_m,0,0, depth_y,0,0,0, 0,0,height_m,0, 0,0,0,1]). \
Right wall: anchor [length_x, 0, z]; same matrix as the left wall. Interior partitions follow \
whichever of these two patterns matches the direction the document implies, anchored so they do \
not overlap other walls.
- Ground slab / intermediate slab: template 0, anchor [0, 0, z], matrix diag [length_x, depth_y, \
slab_height_m] (default 0.2).
- Pitched roof: template 1, anchor [0, 0, z], matrix diag [length_x, depth_y, roof_height_m] \
(default 1.5); this template already encodes the gable shape, so no rotation is needed.
- Door / window: template 0, anchor on the wall it belongs to at a reasonable offset along that \
wall, matrix diag [length_m, 0.08, height_m].
- Column: template 0, matrix diag [length_m or 0.25, width_m or 0.25, height_m].
- Stair flight: template 2 (ramp), anchor at the flight's start point, matrix diag [length_m, \
width_m, height_m] to climb along +X, or [0,-width_m,0,0, length_m,0,0,0, 0,0,height_m,0, \
0,0,0,1] to climb along +Y when the program says the flight turns. A stair landing is template 0.
- Room volume (element type "room"): template 0, matrix diag [length_m, width_m, height_m], \
positioned inside the footprint without overlapping walls; always material index 8.
- Other (paths, porch slabs, railings, steps): template 0; use material index 7 for anything \
described as a path/walkway, otherwise index 1.
- One CityObject per element in the program (respect "quantity" by emitting that many numbered \
objects, e.g. Wall1, Wall2, each with its own anchor vertex).

Material index per element_type (use these exactly, as a list repeated once per template face - 6 \
entries for template 0, 5 entries for templates 1/2): wall=0, slab=1, door=2, window=3, roof=4, \
column=1, stair=6 (landings also 6), room=8, other=7 if path-like else 1. If the input element's \
"notes" mentions an explicit finish/colour, you may still use the closest matching material index \
above - never add a new material.

Rules:
- Every CityObject id used in "children"/"parents" must exist in "CityObjects".
- Every non-Building CityObject's "attributes.element_type" must be exactly the "type" value of \
the input element it came from (wall, slab, roof, stair, door, window, column, room, or other). \
Do not invent new type names and do not skip this field - a later step uses it to color the model.
- "dimensions_m" must be present on every non-Building CityObject and must match the scale values \
used in its "transformationMatrix" (in [length, width, height] order, ignoring sign).
- Output valid, parseable JSON only - no Markdown fences, no comments, no trailing commas."""


class CityJsonGenerationError(RuntimeError):
    """Raised when Gemini's output cannot be parsed/validated at either stage."""

    def __init__(self, message: str, raw_text: str) -> None:
        super().__init__(message)
        self.raw_text = raw_text


def summarize_requirements(document_text: str) -> BuildingRequirements:
    raw_text = gemini_service.generate_json(SUMMARY_SYSTEM_PROMPT, document_text)
    parsed = _loads_json_value(raw_text)
    if not isinstance(parsed, dict):
        raise CityJsonGenerationError(
            "Gemini did not return a JSON object for the requirements summary", raw_text
        )
    try:
        return BuildingRequirements.model_validate(parsed)
    except Exception as exc:
        raise CityJsonGenerationError(
            f"Requirements summary failed validation: {exc}", raw_text
        ) from exc


def generate_cityjson(requirements: BuildingRequirements) -> dict[str, Any]:
    user_text = requirements.model_dump_json(indent=2)
    raw_text = gemini_service.generate_json(CITYJSON_SYSTEM_PROMPT, user_text, temperature=0.1)
    parsed = _loads_json_value(raw_text)
    if not isinstance(parsed, dict):
        raise CityJsonGenerationError("Gemini did not return a JSON object for the CityJSON model", raw_text)

    if parsed.get("type") != "CityJSON":
        raise CityJsonGenerationError(
            "Gemini output is missing \"type\": \"CityJSON\"", json.dumps(parsed)
        )
    if not isinstance(parsed.get("CityObjects"), dict) or not parsed["CityObjects"]:
        raise CityJsonGenerationError("Gemini output has no CityObjects", json.dumps(parsed))
    if not isinstance(parsed.get("vertices"), list) or not parsed["vertices"]:
        raise CityJsonGenerationError("Gemini output has no vertices", json.dumps(parsed))

    templates = parsed.get("geometry-templates", {}).get("templates", [])
    num_vertices = len(parsed["vertices"])
    for obj_id, cityobject in parsed["CityObjects"].items():
        for geom in cityobject.get("geometry", []):
            if geom.get("type") != "GeometryInstance":
                continue
            template_idx = geom.get("template")
            if not isinstance(template_idx, int) or not (0 <= template_idx < len(templates)):
                raise CityJsonGenerationError(
                    f"CityObject {obj_id!r} references missing template {template_idx!r}",
                    json.dumps(parsed),
                )
            anchor = geom.get("boundaries")
            if (
                not isinstance(anchor, list)
                or len(anchor) != 1
                or not isinstance(anchor[0], int)
                or not (0 <= anchor[0] < num_vertices)
            ):
                raise CityJsonGenerationError(
                    f"CityObject {obj_id!r} has an invalid GeometryInstance anchor {anchor!r}",
                    json.dumps(parsed),
                )

    return parsed
