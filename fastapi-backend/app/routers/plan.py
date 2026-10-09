from fastapi import APIRouter, HTTPException

from app.schemas.models import PlanGenerateResponse, TextToIfcRequest
from app.services.bim_llm import ModelNotReadyError, bim_llm, unusable_plan_detail

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/generate", response_model=PlanGenerateResponse)
def generate_plan(request: TextToIfcRequest):
    try:
        result = bim_llm.generate(request.description)
    except ModelNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # MVP: JSON rejection is disabled inside unusable_plan_detail.
    # The call stays so the check can be restored later.
    detail = unusable_plan_detail(result)
    if detail is not None:
        raise HTTPException(status_code=422, detail=detail)

    return {
        "valid_json": result.valid_json,
        "valid_structure": result.valid_structure,
        "plan": result.plan,
        "raw_text": result.raw_text,
    }
