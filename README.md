# BIMMeetGeneratorAgent

A small FastAPI-based converter that turns a JSON building plan into an IFC file using `ifcopenshell`.

## Project overview

This repository contains a JSON-to-IFC conversion service. The backend validates an input building plan, maps elements into IFC geometry, and writes an IFC file to disk.

## Repository structure

- `fastapi-backend/`
  - `app/`
    - `routers/ifc.py` - API endpoints for text and JSON IFC generation.
    - `services/ifc_service.py` - backend logic for saving IFC output.
    - `schemas/models.py` - API request/response models and schema re-exports.
  - `bim_ifc_builder/`
    - `schemas/building_plan.py` - input schema for building plans.
    - `builder/core.py` - main IFC creation and file writing logic.
    - `builder/elements/` - element creator functions for IFC entities.
    - `builder/elements/registry.py` - dispatches supported element types.
    - `utils/placement.py` - placement matrix builder for element position/rotation.
    - `validJsonFiles/` - sample valid JSON payloads.
  - `requirements.txt` - Python dependencies.
  - `output/` - generated IFC file location.

## How it works

1. A JSON payload is sent to `POST /ifc/generate-from-json`.
2. FastAPI validates the payload against the `BuildingPlan` schema.
3. `build_ifc(...)` creates an IFC model using `ifcopenshell`.
4. The service creates floors and places each element into the correct storey.
5. The final IFC file is written to `fastapi-backend/output/generated_model.ifc`.

## Expected JSON structure

The API accepts a `BuildingPlan` object with this shape:

```json
{
  "name": "My Building",
  "building_type": "office",
  "floors": 2,
  "elements": [
    {
      "type": "wall",
      "name": "Exterior Wall",
      "floor": 1,
      "length_m": 10.0,
      "height_m": 3.0,
      "thickness_m": 0.3,
      "position": { "x": 0.0, "y": 0.0, "z": 0.0 },
      "rotation_deg": 0.0
    }
  ]
}
```

### Supported element types

- `wall`
- `slab`
- `column`
- `beam`
- `door`
- `window`

> Note: current element creation only includes `wall` and `slab` in the existing builder implementation.

### Element fields

- `type`: required
- `name`: required
- `floor`: default is `1`
- `length_m`, `width_m`, `depth_m`, `height_m`, `thickness_m`: optional numeric dimensions
- `position`: object with `x`, `y`, `z` coordinates
- `rotation_deg`: rotation angle in degrees

## API endpoints

- `POST /ifc/generate-from-json`
  - Accepts a `BuildingPlan` JSON payload
  - Generates `generated_model.ifc`
  - Returns the file name, output path, and element count

- `GET /ifc/download`
  - Downloads the latest generated IFC file

## Run locally

1. Create and activate a Python environment.
2. Install dependencies:

```bash
cd fastapi-backend
python -m pip install -r requirements.txt
```

3. Start the server:

```bash
cd fastapi-backend
uvicorn app.main:app --reload
```

4. Send JSON payloads to `http://127.0.0.1:8000/ifc/generate-from-json`.

## Sample files

The folder `fastapi-backend/bim_ifc_builder/validJsonFiles/` contains example payloads you can use to test IFC generation.

## Notes

- Output is written to `fastapi-backend/output/generated_model.ifc`.
- The schema uses Pydantic models for request validation.
- `ifcopenshell` must be installed and available for IFC creation.

