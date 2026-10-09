from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas.models import BuildingPlanRequest, JsonToIfcResponse, TextToIfcRequest, TextToIfcResponse
from app.services.bim_llm import ModelNotReadyError, bim_llm, unusable_plan_detail
from app.services.ifc_service import save_ifc_from_plan
from app.services.plan_mapper import PlanMappingError, hierarchical_to_building_plan
from bim_ifc_builder.exceptions import UnsupportedElementTypeError

router = APIRouter(prefix="/ifc", tags=["ifc"])


@router.post("/generate", response_model=TextToIfcResponse)
def generate_ifc(request: TextToIfcRequest):
    try:
        result = bim_llm.generate(request.description)
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # MVP: JSON rejection is disabled inside unusable_plan_detail.
    # The call stays so the check can be restored later.
    detail = unusable_plan_detail(result)
    if detail is not None:
        raise HTTPException(status_code=422, detail=detail)

    if not isinstance(result.plan, dict):
        return {
            "message": "Model response was not a JSON object, so no IFC file was written",
            "file_name": "",
            "output_path": "",
        }

    try:
        plan = hierarchical_to_building_plan(result.plan, fallback_name=request.description)
        output_path = save_ifc_from_plan(plan)
    except PlanMappingError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "valid_json": True,
                "valid_structure": result.valid_structure,
            },
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "message": "IFC file generated successfully",
        "file_name": output_path.name,
        "output_path": str(output_path),
    }


@router.post("/generate-from-json", response_model=JsonToIfcResponse)
def generate_ifc_from_json(plan: BuildingPlanRequest):
    try:
        output_path = save_ifc_from_plan(plan)
    except UnsupportedElementTypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "message": "IFC file generated successfully",
        "file_name": output_path.name,
        "output_path": str(output_path),
        "element_count": len(plan.elements),
    }


@router.get("/download")
def download_ifc():
    file_path = Path(__file__).resolve().parent.parent.parent / "output" / "generated_model.ifc"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="No IFC file has been generated yet")
    return FileResponse(path=file_path, filename=file_path.name, media_type="application/octet-stream")
