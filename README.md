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

- `GET /health`
  - Reports whether the published LoRA adapter finished loading

- `POST /plan/generate`
  - Sends a text description to `Rishi74518/smollm2-360m-bim-lora` on top of `HuggingFaceTB/SmolLM2-360M-Instruct`
  - Returns hierarchical BIM JSON plus `valid_json` and `valid_structure`
  - Invalid model JSON returns 422 with the raw text

- `POST /ifc/generate`
  - Uses the same model, maps walls and slabs into a `BuildingPlan`, and writes an IFC file
  - Other element types are skipped because the builder currently creates walls and slabs
  - Unmappable model JSON returns 422 and does not use the rules-based text stub

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
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

Startup downloads the public base model and the LoRA adapter before the server accepts requests. If that download fails, the process still starts and `GET /health` reports the error. Set `BIM_ADAPTER_PATH` to a local adapter folder to skip the Hub download.

3. Start the server:

```bash
cd fastapi-backend
uvicorn app.main:app --reload
```

4. Send text to `http://127.0.0.1:8000/plan/generate` or JSON payloads to `http://127.0.0.1:8000/ifc/generate-from-json`.

The same app can run later as a free Hugging Face Docker Space. [`fastapi-backend/Dockerfile`](fastapi-backend/Dockerfile) listens on port 7860 and sets `BIM_ADAPTER_ID=Rishi74518/smollm2-360m-bim-lora`.

## Sample files

The folder `fastapi-backend/bim_ifc_builder/validJsonFiles/` contains example payloads you can use to test IFC generation.

## LLM fine-tuning

The [`training/`](training/) package provides a CPU-compatible LoRA workflow for
fine-tuning `HuggingFaceTB/SmolLM2-360M-Instruct` on the 500 hierarchical BIM
examples under [`datasets/`](datasets/). Prefer the notebook
[`training/BIM_LLM_Fine_Tuning.ipynb`](training/BIM_LLM_Fine_Tuning.ipynb).
See [`training/README.md`](training/README.md) for setup details.

## Notes

- Output is written to `fastapi-backend/output/generated_model.ifc`.
- The schema uses Pydantic models for request validation.
- `ifcopenshell` must be installed and available for IFC creation.

