from pydantic import BaseModel, Field

from bim_ifc_builder import BuildingPlan


class TextToIfcRequest(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)


class TextToIfcResponse(BaseModel):
    message: str
    file_name: str
    output_path: str


class JsonToIfcResponse(BaseModel):
    message: str
    file_name: str
    output_path: str
    element_count: int


# Re-export the shared schema used by both text and JSON routes.
BuildingPlanRequest = BuildingPlan
