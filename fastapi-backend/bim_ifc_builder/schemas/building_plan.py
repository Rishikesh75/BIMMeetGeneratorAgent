from typing import Literal

from pydantic import BaseModel, Field


class Position(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class BuildingElement(BaseModel):
    type: Literal["wall", "slab", "column", "beam", "door", "window"]
    name: str
    floor: int = Field(default=1, ge=1)
    length_m: float | None = None
    width_m: float | None = None
    depth_m: float | None = None
    height_m: float | None = None
    thickness_m: float | None = None
    position: Position = Field(default_factory=Position)
    rotation_deg: float = 0.0


class BuildingPlan(BaseModel):
    name: str
    building_type: str = "generic"
    floors: int = Field(default=1, ge=1)
    elements: list[BuildingElement] = Field(default_factory=list)
