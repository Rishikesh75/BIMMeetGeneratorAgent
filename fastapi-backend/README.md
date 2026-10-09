---
title: BIM Meet Generator
emoji: "🏢"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# BIM Meet Generator

FastAPI service that loads the public base model `HuggingFaceTB/SmolLM2-360M-Instruct` plus the published LoRA `Rishi74518/smollm2-360m-bim-lora` on CPU.

`BIM_ADAPTER_ID` defaults to `Rishi74518/smollm2-360m-bim-lora`. Override it in the Space settings if the adapter repo changes. A public adapter does not need a token.

## Endpoints

- `GET /health` — whether the adapter finished loading
- `POST /plan/generate` — text to hierarchical BIM JSON
- `POST /ifc/generate` — text to IFC, using walls and slabs from the model JSON
- `POST /ifc/generate-from-json` — flat `BuildingPlan` JSON to IFC
- `GET /ifc/download` — latest IFC file

The free CPU Space sleeps when idle. The first request after sleep waits while the weights load.

## Local run

From this directory, install the CPU wheel before the rest of the requirements so pip does not pull a CUDA build:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Set `BIM_ADAPTER_PATH` to a local adapter folder to skip the Hub download.
