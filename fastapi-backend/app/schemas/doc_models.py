"""Schemas for the document -> Gemini -> CityJSON -> IFC pipeline.

Kept separate from app/schemas/models.py so the existing text/JSON IFC routes
are untouched by this feature.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RequirementElement(BaseModel):
    """One requested building component extracted from the source document."""

    type: str = Field(..., description="wall, slab, roof, stair, door, window, column, room, other")
    name: str
    storey: str = Field(default="Storey1", description="Name of the storey this element belongs to")
    quantity: int = Field(default=1, ge=1)
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    notes: Optional[str] = None


class RequirementStorey(BaseModel):
    name: str
    elevation_m: float = 0.0
    height_m: float = 3.0


class BuildingRequirements(BaseModel):
    """Structured output of the summarization agent (Gemini step 1)."""

    building_name: str
    building_type: str = "generic"
    storeys: list[RequirementStorey] = Field(default_factory=list)
    elements: list[RequirementElement] = Field(default_factory=list)
    summary: str = ""


class DocToIfcResponse(BaseModel):
    message: str
    file_name: str
    output_path: str
    city_object_count: int
    requirements: BuildingRequirements
    cityjson: dict[str, Any]
