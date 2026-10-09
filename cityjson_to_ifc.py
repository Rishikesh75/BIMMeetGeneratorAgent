"""Convert a CityJSON file to IFC using IfcOpenShell.

Usage:
    python cityjson_to_ifc.py [input.city.json] [output.ifc]

Defaults to converting simple.city.json -> simple.ifc in this folder.

Requires: ifcopenshell  (pip install ifcopenshell)
"""

import json
import sys
import time
import uuid
from pathlib import Path

import ifcopenshell
import ifcopenshell.guid


def ifc_guid():
    return ifcopenshell.guid.compress(uuid.uuid4().hex)


def load_cityjson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def real_vertices(cj):
    """Return vertices in real-world coordinates, applying the transform if present."""
    verts = cj.get("vertices", [])
    transform = cj.get("transform")
    if not transform:
        return [list(map(float, v)) for v in verts]

    sx, sy, sz = transform.get("scale", [1.0, 1.0, 1.0])
    tx, ty, tz = transform.get("translate", [0.0, 0.0, 0.0])
    return [
        [v[0] * sx + tx, v[1] * sy + ty, v[2] * sz + tz]
        for v in verts
    ]


def iter_surfaces(boundaries, geom_type):
    """Yield each surface (a list of rings) regardless of geometry nesting depth.

    MultiSurface/CompositeSurface : [surface, ...]
    Solid                         : [shell, ...] -> [surface, ...]
    MultiSolid/CompositeSolid     : [solid, ...] -> [shell, ...] -> [surface, ...]
    """
    gt = (geom_type or "").lower()
    if gt in ("multisurface", "compositesurface"):
        shells = [boundaries]
    elif gt == "solid":
        shells = boundaries
    elif gt in ("multisolid", "compositesolid"):
        shells = [shell for solid in boundaries for shell in solid]
    else:
        # Fall back to treating boundaries as a single shell of surfaces.
        shells = [boundaries]

    for shell in shells:
        for surface in shell:
            yield surface


def iter_surfaces_with_material(boundaries, geom_type, mat_values):
    """Like iter_surfaces, but also yields the material index for each surface.

    ``mat_values`` mirrors the boundary nesting minus the ring level. When it is
    missing or shorter than the surfaces, ``None`` is yielded instead.
    """
    gt = (geom_type or "").lower()
    if gt in ("multisurface", "compositesurface"):
        shells = [boundaries]
        mat_shells = [mat_values]
    elif gt == "solid":
        shells = boundaries
        mat_shells = mat_values if mat_values is not None else [None] * len(boundaries)
    elif gt in ("multisolid", "compositesolid"):
        shells = [shell for solid in boundaries for shell in solid]
        if mat_values is not None:
            mat_shells = [shell for solid in mat_values for shell in solid]
        else:
            mat_shells = [None] * len(shells)
    else:
        shells = [boundaries]
        mat_shells = [mat_values]

    for shell, mat_shell in zip(shells, mat_shells):
        for i, surface in enumerate(shell):
            material = None
            if isinstance(mat_shell, list) and i < len(mat_shell):
                material = mat_shell[i]
            yield surface, material


def apply_matrix(matrix, vertex):
    """Apply a row-major 4x4 transformation matrix to a 3D point."""
    m = matrix
    x, y, z = vertex
    tx = m[0] * x + m[1] * y + m[2] * z + m[3]
    ty = m[4] * x + m[5] * y + m[6] * z + m[7]
    tz = m[8] * x + m[9] * y + m[10] * z + m[11]
    w = m[12] * x + m[13] * y + m[14] * z + m[15]
    if w and w != 1.0:
        tx, ty, tz = tx / w, ty / w, tz / w
    return [tx, ty, tz]


def instance_geometry(geom, vertices, templates, template_vertices):
    """Resolve a GeometryInstance into (real vertices, boundaries, type)."""
    template = templates[geom["template"]]
    anchor = vertices[geom["boundaries"][0]]
    matrix = geom.get(
        "transformationMatrix", [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    )
    verts = [
        [c + a for c, a in zip(apply_matrix(matrix, v), anchor)]
        for v in template_vertices
    ]
    return verts, template.get("boundaries", []), template.get("type")


def build_face_sets(ifc, verts, boundaries, geom_type, mat_values):
    """Create IfcPolygonalFaceSets grouped by material index.

    Surfaces that share a material index are merged into a single face set so
    each colour can be applied with one IfcStyledItem. Returns a list of
    ``(face_set, material_index)`` tuples.
    """
    groups = {}  # material index -> {"index": {...}, "verts": [...], "faces": [...]}
    for surface, material in iter_surfaces_with_material(
        boundaries, geom_type, mat_values
    ):
        if not surface:
            continue
        group = groups.setdefault(material, {"index": {}, "verts": [], "faces": []})
        exterior = surface[0]  # outer ring; inner rings/holes ignored for simplicity
        coord_index = []
        for idx in exterior:
            local = group["index"].get(idx)
            if local is None:
                group["verts"].append(verts[idx])
                local = len(group["verts"])  # IFC indices are 1-based
                group["index"][idx] = local
            coord_index.append(local)
        group["faces"].append(
            ifc.create_entity("IfcIndexedPolygonalFace", CoordIndex=coord_index)
        )

    closed = (geom_type or "").lower() == "solid" and len(groups) == 1
    face_sets = []
    for material, group in groups.items():
        if not group["faces"]:
            continue
        point_list = ifc.create_entity(
            "IfcCartesianPointList3D",
            CoordList=[tuple(v) for v in group["verts"]],
        )
        face_set = ifc.create_entity(
            "IfcPolygonalFaceSet",
            Coordinates=point_list,
            Closed=closed,
            Faces=group["faces"],
        )
        face_sets.append((face_set, material))
    return face_sets


def geometry_material_values(geom):
    """Return the first material theme's values array for a geometry, or None."""
    material = geom.get("material")
    if not material:
        return None
    for theme in material.values():
        values = theme.get("values")
        if values is not None:
            return values
    return None


def add_geometry(
    ifc, context, vertices, cityobject, templates, template_vertices, surface_style
):
    """Create IfcPolygonalFaceSet shape representations for one CityObject."""
    items = []
    for geom in cityobject.get("geometry", []):
        gtype = geom.get("type", "")
        if gtype == "GeometryInstance":
            verts, boundaries, inner_type = instance_geometry(
                geom, vertices, templates, template_vertices
            )
            mat_values = None
        else:
            verts, boundaries, inner_type = vertices, geom.get("boundaries", []), gtype
            mat_values = geometry_material_values(geom)

        for face_set, material in build_face_sets(
            ifc, verts, boundaries, inner_type, mat_values
        ):
            items.append(face_set)
            style = surface_style(material)
            if style is not None:
                ifc.create_entity(
                    "IfcStyledItem", Item=face_set, Styles=[style]
                )

    if not items:
        return None

    return ifc.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="Tessellation",
        Items=items,
    )


def build_ifc(cj, output_path):
    vertices = real_vertices(cj)

    gt = cj.get("geometry-templates", {})
    templates = gt.get("templates", [])
    template_vertices = [list(map(float, v)) for v in gt.get("vertices-templates", [])]

    ifc = ifcopenshell.file(schema="IFC4")

    # --- Units ---
    length_unit = ifc.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE")
    unit_assignment = ifc.create_entity("IfcUnitAssignment", Units=[length_unit])

    # --- Geometric context ---
    origin = ifc.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    axis = ifc.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    ref_dir = ifc.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
    world_cs = ifc.create_entity(
        "IfcAxis2Placement3D", Location=origin, Axis=axis, RefDirection=ref_dir
    )
    context = ifc.create_entity(
        "IfcGeometricRepresentationContext",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-5,
        WorldCoordinateSystem=world_cs,
    )

    # --- Owner history ---
    person = ifc.create_entity("IfcPerson", FamilyName="Converter")
    organization = ifc.create_entity("IfcOrganization", Name="CityJSON-to-IFC")
    person_and_org = ifc.create_entity(
        "IfcPersonAndOrganization",
        ThePerson=person,
        TheOrganization=organization,
    )
    application = ifc.create_entity(
        "IfcApplication",
        ApplicationDeveloper=organization,
        Version="1.0",
        ApplicationFullName="CityJSON to IFC Converter",
        ApplicationIdentifier="cityjson_to_ifc",
    )
    owner_history = ifc.create_entity(
        "IfcOwnerHistory",
        OwningUser=person_and_org,
        OwningApplication=application,
        ChangeAction="ADDED",
        CreationDate=int(time.time()),
    )

    def placement():
        return ifc.create_entity("IfcLocalPlacement", RelativePlacement=world_cs)

    # --- Appearance materials -> cached IfcSurfaceStyle ---
    materials = cj.get("appearance", {}).get("materials", [])
    style_cache = {}

    def surface_style(material_index):
        if material_index is None or not (0 <= material_index < len(materials)):
            return None
        if material_index in style_cache:
            return style_cache[material_index]
        mat = materials[material_index]
        rgb = mat.get("diffuseColor", [0.8, 0.8, 0.8])
        colour = ifc.create_entity(
            "IfcColourRgb",
            Red=float(rgb[0]),
            Green=float(rgb[1]),
            Blue=float(rgb[2]),
        )
        rendering = ifc.create_entity(
            "IfcSurfaceStyleRendering",
            SurfaceColour=colour,
            Transparency=float(mat.get("transparency", 0.0)),
            ReflectanceMethod="NOTDEFINED",
        )
        style = ifc.create_entity(
            "IfcSurfaceStyle",
            Name=mat.get("name"),
            Side="BOTH",
            Styles=[rendering],
        )
        style_cache[material_index] = style
        return style

    # --- Spatial structure: Project -> Site -> Building -> Storey ---
    project = ifc.create_entity(
        "IfcProject",
        GlobalId=ifc_guid(),
        OwnerHistory=owner_history,
        Name="CityJSON Conversion",
        UnitsInContext=unit_assignment,
        RepresentationContexts=[context],
    )
    site = ifc.create_entity(
        "IfcSite",
        GlobalId=ifc_guid(),
        OwnerHistory=owner_history,
        Name="Site",
        ObjectPlacement=placement(),
        CompositionType="ELEMENT",
    )
    building = ifc.create_entity(
        "IfcBuilding",
        GlobalId=ifc_guid(),
        OwnerHistory=owner_history,
        Name="Building",
        ObjectPlacement=placement(),
        CompositionType="ELEMENT",
    )
    storey = ifc.create_entity(
        "IfcBuildingStorey",
        GlobalId=ifc_guid(),
        OwnerHistory=owner_history,
        Name="Storey",
        ObjectPlacement=placement(),
        CompositionType="ELEMENT",
    )

    ifc.create_entity(
        "IfcRelAggregates",
        GlobalId=ifc_guid(),
        OwnerHistory=owner_history,
        RelatingObject=project,
        RelatedObjects=[site],
    )
    ifc.create_entity(
        "IfcRelAggregates",
        GlobalId=ifc_guid(),
        OwnerHistory=owner_history,
        RelatingObject=site,
        RelatedObjects=[building],
    )
    ifc.create_entity(
        "IfcRelAggregates",
        GlobalId=ifc_guid(),
        OwnerHistory=owner_history,
        RelatingObject=building,
        RelatedObjects=[storey],
    )

    # --- City objects -> IfcBuildingElementProxy ---
    products = []
    for obj_id, cityobject in cj.get("CityObjects", {}).items():
        representation = add_geometry(
            ifc, context, vertices, cityobject, templates, template_vertices, surface_style
        )

        product_rep = None
        if representation is not None:
            product_rep = ifc.create_entity(
                "IfcProductDefinitionShape", Representations=[representation]
            )

        proxy = ifc.create_entity(
            "IfcBuildingElementProxy",
            GlobalId=ifc_guid(),
            OwnerHistory=owner_history,
            Name=obj_id,
            ObjectType=cityobject.get("type"),
            ObjectPlacement=placement(),
            Representation=product_rep,
        )
        products.append(proxy)

    if products:
        ifc.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=ifc_guid(),
            OwnerHistory=owner_history,
            RelatingStructure=storey,
            RelatedElements=products,
        )

    ifc.write(str(output_path))
    return len(products)


def main():
    here = Path(__file__).resolve().parent
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "simple.city.json"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_suffix("").with_suffix(".ifc")

    cj = load_cityjson(input_path)
    if cj.get("type") != "CityJSON":
        raise SystemExit(f"{input_path} is not a CityJSON file.")

    count = build_ifc(cj, output_path)
    print(f"Converted {count} city object(s) -> {output_path}")


if __name__ == "__main__":
    main()
