class UnsupportedElementTypeError(ValueError):
    """Raised when a building plan contains an element type the builder cannot create."""


class InvalidBuildingPlanError(ValueError):
    """Raised when a building plan fails validation before IFC generation."""
