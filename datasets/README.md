# BIM Training Datasets

This folder contains training datasets for converting natural-language building requests into hierarchical JSON aligned with [`docs/valid-structure.json`](../docs/valid-structure.json).

## Dataset levels

| Level | Focus | File | Records | Status |
|------:|-------|------|--------:|--------|
| 1 | Single element (walls) | [`level-01-single-wall.jsonl`](level-01-single-wall.jsonl) | 50 | Available |
| 2 | Multiple elements | [`level-02-multiple-elements.jsonl`](level-02-multiple-elements.jsonl) | 50 | Available |
| 3 | Geometry | [`level-03-geometry.jsonl`](level-03-geometry.jsonl) | 50 | Available |
| 4 | Openings | [`level-04-openings.jsonl`](level-04-openings.jsonl) | 50 | Available |
| 5 | Multiple rooms | [`level-05-multiple-rooms.jsonl`](level-05-multiple-rooms.jsonl) | 50 | Available |
| 6 | Multiple storeys | [`level-06-multiple-storeys.jsonl`](level-06-multiple-storeys.jsonl) | 50 | Available |
| 7 | Complex buildings | [`level-07-complex-buildings.jsonl`](level-07-complex-buildings.jsonl) | 50 | Available |
| 8 | Materials | [`level-08-materials.jsonl`](level-08-materials.jsonl) | 50 | Available |
| 9 | Relationships | [`level-09-relationships.jsonl`](level-09-relationships.jsonl) | 50 | Available |
| 10 | Complete IFC-ready buildings | [`level-10-complete-ifc-ready-buildings.jsonl`](level-10-complete-ifc-ready-buildings.jsonl) | 50 | Available |

**Total:** 500 records across all levels.

## Record contract

Each line is a JSON object:

```json
{
  "input": "Natural-language building request",
  "output": { "...hierarchical building JSON..." }
}
```

Every `output` includes:

- `project`, `site`, `building`, `storeys`, `elements`, `materials`, `relationships`, `metadata`
- Meters and `right_handed_z_up` coordinates
- `metadata.dataset_level` matching the dataset level

## Cumulative capability matrix

Levels are **cumulative**: each level includes everything from earlier levels plus new capabilities.

| Capability | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 |
|------------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:---:|
| Single wall | x | | | | | | | | | |
| Multiple structural elements | | x | x | x | x | x | x | x | x | x |
| Rich geometry (diagonal lines, complex outlines) | | | x | x | x | x | x | x | x | x |
| Doors and windows | | | | x | x | x | x | x | x | x |
| Multiple rooms (`spaces`) | | | | | x | x | x | x | x | x |
| Multiple storeys and stairs | | | | | | x | x | x | x | x |
| Roofs and complex layouts | | | | | | | x | x | x | x |
| Material definitions and references | | | | | | | | x | x | x |
| Relationship graph | | | | | | | | | x | x |
| Fully populated IFC-ready model | | | | | | | | | | x |

## Per-level constraints

### Level 1
- Exactly one storey and one wall
- All other element collections, `materials`, and `relationships` are empty

### Level 2
- One storey
- At least two structural elements from `walls`, `slabs`, `columns`, `beams`
- No openings, rooms, roofs, stairs, materials, or relationships

### Level 3
- Level 2 plus geometry variation:
  - Diagonal walls, non-rectangular slab outlines, or diagonal beams

### Level 4
- Level 3 plus at least one door or window
- Openings must reference a valid `host_wall` and fit within wall dimensions

### Level 5
- Level 4 plus at least two `spaces` with valid outlines, usages, and storey references

### Level 6
- Level 5 plus at least two storeys
- Stairs linking valid adjacent storeys
- Elements and spaces distributed across storeys

### Level 7
- Level 6 plus roofs and richer building combinations

### Level 8
- Level 7 plus material definitions in `materials`
- All populated physical elements reference defined materials

### Level 9
- Level 8 plus `relationships` with valid endpoints
- Relationship types include: `contains`, `hosts`, `connects`, `bounds_space`, `assigns_material`

### Level 10
- Complete hierarchical building models
- All element collections populated
- Comprehensive materials and relationships
- Internally consistent IDs and references

## Regeneration and validation

Generate Level 1:

```bash
python fastapi-backend/scripts/generate_level_01_dataset.py
```

Generate Levels 2–10:

```bash
python fastapi-backend/scripts/generate_levels_02_10_datasets.py
```

Validate Level 1:

```bash
python fastapi-backend/scripts/validate_level_01_dataset.py
```

Validate Levels 2–10:

```bash
python fastapi-backend/scripts/validate_levels_02_10_datasets.py
```

## Note on current API schema

These hierarchical datasets are a future-facing training format. They are separate from the current flat `BuildingPlan` schema used by the FastAPI IFC generation endpoint.
