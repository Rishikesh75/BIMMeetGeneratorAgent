from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.doc_models import DocToIfcResponse
from app.services.cityjson_ifc_bridge import save_ifc_from_cityjson
from app.services.cityjson_materials import apply_materials
from app.services.doc_text_extractor import UnsupportedDocumentError, extract_text
from app.services.doc_to_cityjson import (
    CityJsonGenerationError,
    generate_cityjson,
    summarize_requirements,
)
from app.services.gemini_client import GeminiNotConfiguredError

router = APIRouter(prefix="/doc", tags=["doc"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/generate-ifc", response_model=DocToIfcResponse)
async def generate_ifc_from_document(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB upload limit")

    try:
        document_text = extract_text(file.filename or "", file.content_type or "", data)
    except UnsupportedDocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        requirements = summarize_requirements(document_text)
        cityjson = generate_cityjson(requirements)
        cityjson = apply_materials(cityjson)
    except GeminiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CityJsonGenerationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": str(exc), "raw_text": exc.raw_text},
        ) from exc

    try:
        output_path, city_object_count = save_ifc_from_cityjson(cityjson)
    except Exception as exc:  # pragma: no cover - defensive path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "message": "IFC file generated successfully from document",
        "file_name": output_path.name,
        "output_path": str(output_path),
        "city_object_count": city_object_count,
        "requirements": requirements,
        "cityjson": cityjson,
    }
