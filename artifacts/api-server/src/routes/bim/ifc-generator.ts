import { generateContentText } from "@workspace/integrations-gemini-server";

/** Gemini model id for native `generateContent` (see https://ai.google.dev/gemini-api/docs/models ). */
const BIM_EXTRACTION_MODEL =
  process.env.BIM_EXTRACTION_MODEL?.trim() || "gemini-flash-latest";

export interface ExtractedBimElements {
  spaces: BimSpace[];
  walls: BimWall[];
  doors: BimDoor[];
  windows: BimWindow[];
  columns: BimColumn[];
  beams: BimBeam[];
  slabs: BimSlab[];
  projectName: string;
  projectDescription: string;
  buildingName: string;
}

export interface BimSpace {
  name: string;
  area?: number;
  description?: string;
}

export interface BimWall {
  name: string;
  height?: number;
  thickness?: number;
  material?: string;
}

export interface BimDoor {
  name: string;
  width?: number;
  height?: number;
  material?: string;
}

export interface BimWindow {
  name: string;
  width?: number;
  height?: number;
}

export interface BimColumn {
  name: string;
  height?: number;
  crossSection?: string;
  material?: string;
}

export interface BimBeam {
  name: string;
  span?: number;
  crossSection?: string;
  material?: string;
}

export interface BimSlab {
  name: string;
  thickness?: number;
  area?: number;
  material?: string;
}

export async function extractBimElementsFromNotes(
  meetingNotes: string,
  meetingTitle?: string,
): Promise<ExtractedBimElements> {
  const prompt = `You are a BIM (Building Information Modeling) expert. Analyze the following meeting notes from a construction/architecture/engineering project meeting and extract all building elements mentioned or implied.

Meeting Title: ${meetingTitle || "Untitled Meeting"}
Meeting Notes:
${meetingNotes}

Extract the following information and return it as valid JSON matching this exact structure. If an element type is not mentioned, return an empty array for it. Infer reasonable defaults (e.g., standard wall heights 3m, typical thicknesses) when not explicitly stated:

{
  "projectName": "string - name of the project",
  "projectDescription": "string - brief description of the project",
  "buildingName": "string - name of the building",
  "spaces": [{"name": "string", "area": number_or_null, "description": "string"}],
  "walls": [{"name": "string", "height": number_meters_or_null, "thickness": number_meters_or_null, "material": "string_or_null"}],
  "doors": [{"name": "string", "width": number_meters_or_null, "height": number_meters_or_null, "material": "string_or_null"}],
  "windows": [{"name": "string", "width": number_meters_or_null, "height": number_meters_or_null}],
  "columns": [{"name": "string", "height": number_meters_or_null, "crossSection": "string_or_null", "material": "string_or_null"}],
  "beams": [{"name": "string", "span": number_meters_or_null, "crossSection": "string_or_null", "material": "string_or_null"}],
  "slabs": [{"name": "string", "thickness": number_meters_or_null, "area": number_sqm_or_null, "material": "string_or_null"}]
}

Return ONLY the JSON, no markdown, no explanation.`;

  let content: string;
  try {
    const raw = await generateContentText(prompt, {
      model: BIM_EXTRACTION_MODEL,
      maxOutputTokens: 8192,
    });
    content = raw.trim() || "{}";
  } catch (err: unknown) {
    const e = err as { status?: number; message?: string; error?: unknown };
    const msg = e?.message ?? String(err);
    const statusMatch = /\(HTTP (\d+)\)/.exec(msg);
    const status = e?.status ?? (statusMatch ? Number(statusMatch[1]) : undefined);
    const detail =
      e?.error !== undefined ? ` ${JSON.stringify(e.error)}` : "";
    const hint403 =
      status === 403
        ? " Common causes: API key invalid/revoked; key restricted (use “Generative Language API” or no restriction in Google Cloud → Credentials); or enable the Generative Language API for the project. Create keys in Google AI Studio: https://aistudio.google.com/apikey"
        : "";
    const hint400 =
      status === 400
        ? " Often: wrong model id for native generateContent (try BIM_EXTRACTION_MODEL=gemini-flash-latest or another id from https://ai.google.dev/gemini-api/docs/models), or invalid request body."
        : "";
    throw new Error(
      `Gemini request failed${status != null ? ` (HTTP ${status})` : ""}: ${msg}.${detail}${hint403}${hint400}`,
    );
  }

  try {
    const parsed = JSON.parse(content);
    return {
      projectName: parsed.projectName || meetingTitle || "Unnamed Project",
      projectDescription: parsed.projectDescription || "",
      buildingName: parsed.buildingName || "Building 1",
      spaces: parsed.spaces || [],
      walls: parsed.walls || [],
      doors: parsed.doors || [],
      windows: parsed.windows || [],
      columns: parsed.columns || [],
      beams: parsed.beams || [],
      slabs: parsed.slabs || [],
    };
  } catch {
    return {
      projectName: meetingTitle || "Unnamed Project",
      projectDescription: "",
      buildingName: "Building 1",
      spaces: [],
      walls: [],
      doors: [],
      windows: [],
      columns: [],
      beams: [],
      slabs: [],
    };
  }
}

function generateGuid(index: number): string {
  const timestamp = Date.now().toString(16).padStart(12, "0");
  const idx = index.toString(16).padStart(4, "0");
  return `${timestamp.slice(0, 8)}-${timestamp.slice(8, 12)}-4${idx.slice(0, 3)}-8${idx.slice(0, 3)}-${Math.random().toString(16).slice(2, 14).padStart(12, "0")}`.toUpperCase();
}

export function generateIfcFile(
  elements: ExtractedBimElements,
  meetingTitle?: string,
  meetingDate?: string,
): string {
  const timestamp = meetingDate
    ? new Date(meetingDate).toISOString().replace("T", "").replace(/\..+/, "")
    : new Date().toISOString().replace("T", "").replace(/\..+/, "");

  let guidCounter = 1;
  const guid = () => generateGuid(guidCounter++);

  const projectGuid = guid();
  const ownerGuid = guid();
  const siteGuid = guid();
  const buildingGuid = guid();
  const storeyGuid = guid();
  const contextGuid = guid();
  const personGuid = guid();
  const orgGuid = guid();
  const applicationGuid = guid();
  const unitGuid = guid();

  const lines: string[] = [];

  lines.push(`ISO-10303-21;`);
  lines.push(`HEADER;`);
  lines.push(`FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'), '2;1');`);
  lines.push(`FILE_NAME('${elements.projectName}.ifc', '${timestamp}', ('BIM Generator'), ('GMeet BIM Plugin'), 'IFC4', '', '');`);
  lines.push(`FILE_SCHEMA(('IFC4'));`);
  lines.push(`ENDSEC;`);
  lines.push(`DATA;`);

  let entityId = 1;
  const getId = () => `#${entityId++}`;

  const projectId = getId();
  const contextId = getId();
  const personId = getId();
  const orgId = getId();
  const personAndOrgId = getId();
  const applicationId = getId();
  const ownerHistoryId = getId();
  const unitAssignmentId = getId();
  const lengthUnitId = getId();
  const areaUnitId = getId();
  const volumeUnitId = getId();
  const siteId = getId();
  const buildingId = getId();
  const storeyId = getId();
  const storeyPlacementId = getId();
  const storeyAxisId = getId();
  const storeyDirectionId = getId();
  const placementId = getId();
  const axisId = getId();
  const directionId = getId();
  const sitePlacementId = getId();
  const siteAxisId = getId();
  const siteDirectionId = getId();
  const originId = getId();
  const buildingPlacementId = getId();
  const buildingAxisId = getId();
  const buildingDirectionId = getId();
  const projDirectionId = getId();

  lines.push(`${projectId}= IFCPROJECT('${projectGuid}',${ownerHistoryId},'${elements.projectName}','${elements.projectDescription}',$,$,$,(${contextId}),${unitAssignmentId});`);
  lines.push(`${contextId}= IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,${placementId},${projDirectionId});`);
  lines.push(`${personId}= IFCPERSON($,'BIM Generator','GMeet',$,$,$,$,$);`);
  lines.push(`${orgId}= IFCORGANIZATION($,'GMeet BIM Plugin',$,$,$);`);
  lines.push(`${personAndOrgId}= IFCPERSONANDORGANIZATION(${personId},${orgId},$);`);
  lines.push(`${applicationId}= IFCAPPLICATION(${orgId},'1.0','GMeet BIM Generator','GMeetBIM');`);
  lines.push(`${ownerHistoryId}= IFCOWNERHISTORY(${personAndOrgId},${applicationId},$,.ADDED.,$,${personAndOrgId},${applicationId},0);`);
  lines.push(`${unitAssignmentId}= IFCUNITASSIGNMENT((${lengthUnitId},${areaUnitId},${volumeUnitId}));`);
  lines.push(`${lengthUnitId}= IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);`);
  lines.push(`${areaUnitId}= IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);`);
  lines.push(`${volumeUnitId}= IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);`);

  lines.push(`${originId}= IFCCARTESIANPOINT((0.,0.,0.));`);
  lines.push(`${projDirectionId}= IFCDIRECTION((0.,1.));`);
  lines.push(`${siteAxisId}= IFCDIRECTION((0.,0.,1.));`);
  lines.push(`${siteDirectionId}= IFCDIRECTION((1.,0.,0.));`);
  lines.push(`${sitePlacementId}= IFCAXIS2PLACEMENT3D(${originId},${siteAxisId},${siteDirectionId});`);
  lines.push(`${siteId}= IFCSITE('${guid()}',${ownerHistoryId},'Site',$,'IfcSite',$,${sitePlacementId},$,.ELEMENT.,$,$,$,$,$);`);

  lines.push(`${buildingAxisId}= IFCDIRECTION((0.,0.,1.));`);
  lines.push(`${buildingDirectionId}= IFCDIRECTION((1.,0.,0.));`);
  lines.push(`${buildingPlacementId}= IFCAXIS2PLACEMENT3D(${originId},${buildingAxisId},${buildingDirectionId});`);
  lines.push(`${placementId}= IFCLOCALPLACEMENT($,${buildingPlacementId});`);
  lines.push(`${axisId}= IFCDIRECTION((0.,0.,1.));`);
  lines.push(`${directionId}= IFCDIRECTION((1.,0.,0.));`);
  lines.push(`${buildingId}= IFCBUILDING('${guid()}',${ownerHistoryId},'${elements.buildingName}',$,'IfcBuilding',${placementId},$,$,.ELEMENT.,$,$,$);`);

  lines.push(`${storeyAxisId}= IFCDIRECTION((0.,0.,1.));`);
  lines.push(`${storeyDirectionId}= IFCDIRECTION((1.,0.,0.));`);
  const storeyOriginId = getId();
  lines.push(`${storeyOriginId}= IFCCARTESIANPOINT((0.,0.,0.));`);
  lines.push(`${storeyPlacementId}= IFCAXIS2PLACEMENT3D(${storeyOriginId},${storeyAxisId},${storeyDirectionId});`);
  const storeyLocalId = getId();
  lines.push(`${storeyLocalId}= IFCLOCALPLACEMENT(${placementId},${storeyPlacementId});`);
  lines.push(`${storeyId}= IFCBUILDINGSTOREY('${guid()}',${ownerHistoryId},'Ground Floor',$,'IfcBuildingStorey',${storeyLocalId},$,$,.ELEMENT.,0.);`);

  const spaceIds: string[] = [];
  for (const space of elements.spaces) {
    const spId = getId();
    const spPlId = getId();
    const spAxId = getId();
    const spDrId = getId();
    const spOriginId = getId();
    const spLocalId = getId();
    lines.push(`${spOriginId}= IFCCARTESIANPOINT((0.,0.,0.));`);
    lines.push(`${spAxId}= IFCDIRECTION((0.,0.,1.));`);
    lines.push(`${spDrId}= IFCDIRECTION((1.,0.,0.));`);
    lines.push(`${spPlId}= IFCAXIS2PLACEMENT3D(${spOriginId},${spAxId},${spDrId});`);
    lines.push(`${spLocalId}= IFCLOCALPLACEMENT(${storeyLocalId},${spPlId});`);
    lines.push(`${spId}= IFCSPACE('${guid()}',${ownerHistoryId},'${space.name}','${space.description || ""}','IfcSpace',${spLocalId},$,$,.ELEMENT.,.INTERNAL.,$);`);
    spaceIds.push(spId);
  }

  const wallIds: string[] = [];
  for (const wall of elements.walls) {
    const wId = getId();
    const wPlId = getId();
    const wAxId = getId();
    const wDrId = getId();
    const wOriginId = getId();
    const wLocalId = getId();
    lines.push(`${wOriginId}= IFCCARTESIANPOINT((0.,0.,0.));`);
    lines.push(`${wAxId}= IFCDIRECTION((0.,0.,1.));`);
    lines.push(`${wDrId}= IFCDIRECTION((1.,0.,0.));`);
    lines.push(`${wPlId}= IFCAXIS2PLACEMENT3D(${wOriginId},${wAxId},${wDrId});`);
    lines.push(`${wLocalId}= IFCLOCALPLACEMENT(${storeyLocalId},${wPlId});`);
    lines.push(`${wId}= IFCWALLSTANDARDCASE('${guid()}',${ownerHistoryId},'${wall.name}','${wall.material ? `Material: ${wall.material}` : ""}','IfcWall',${wLocalId},$,$,.SOLIDWALL.);`);
    wallIds.push(wId);
  }

  const doorIds: string[] = [];
  for (const door of elements.doors) {
    const dId = getId();
    const dPlId = getId();
    const dAxId = getId();
    const dDrId = getId();
    const dOriginId = getId();
    const dLocalId = getId();
    lines.push(`${dOriginId}= IFCCARTESIANPOINT((0.,0.,0.));`);
    lines.push(`${dAxId}= IFCDIRECTION((0.,0.,1.));`);
    lines.push(`${dDrId}= IFCDIRECTION((1.,0.,0.));`);
    lines.push(`${dPlId}= IFCAXIS2PLACEMENT3D(${dOriginId},${dAxId},${dDrId});`);
    lines.push(`${dLocalId}= IFCLOCALPLACEMENT(${storeyLocalId},${dPlId});`);
    const dTypeId = getId();
    lines.push(`${dTypeId}= IFCDOORTYPE('${guid()}',${ownerHistoryId},'${door.name} Type',$,'IfcDoorType',$,$,$,.NOTDEFINED.,.NOTDEFINED.,${door.height || 2.1},${door.width || 0.9},$);`);
    lines.push(`${dId}= IFCDOOR('${guid()}',${ownerHistoryId},'${door.name}','${door.material || ""}','IfcDoor',${dLocalId},$,$,${door.height || 2.1},${door.width || 0.9});`);
    doorIds.push(dId);
  }

  const windowIds: string[] = [];
  for (const win of elements.windows) {
    const wiId = getId();
    const wiPlId = getId();
    const wiAxId = getId();
    const wiDrId = getId();
    const wiOriginId = getId();
    const wiLocalId = getId();
    lines.push(`${wiOriginId}= IFCCARTESIANPOINT((0.,0.,0.));`);
    lines.push(`${wiAxId}= IFCDIRECTION((0.,0.,1.));`);
    lines.push(`${wiDrId}= IFCDIRECTION((1.,0.,0.));`);
    lines.push(`${wiPlId}= IFCAXIS2PLACEMENT3D(${wiOriginId},${wiAxId},${wiDrId});`);
    lines.push(`${wiLocalId}= IFCLOCALPLACEMENT(${storeyLocalId},${wiPlId});`);
    lines.push(`${wiId}= IFCWINDOW('${guid()}',${ownerHistoryId},'${win.name}','','IfcWindow',${wiLocalId},$,$,${win.height || 1.2},${win.width || 1.0});`);
    windowIds.push(wiId);
  }

  const columnIds: string[] = [];
  for (const col of elements.columns) {
    const cId = getId();
    const cPlId = getId();
    const cAxId = getId();
    const cDrId = getId();
    const cOriginId = getId();
    const cLocalId = getId();
    lines.push(`${cOriginId}= IFCCARTESIANPOINT((0.,0.,0.));`);
    lines.push(`${cAxId}= IFCDIRECTION((0.,0.,1.));`);
    lines.push(`${cDrId}= IFCDIRECTION((1.,0.,0.));`);
    lines.push(`${cPlId}= IFCAXIS2PLACEMENT3D(${cOriginId},${cAxId},${cDrId});`);
    lines.push(`${cLocalId}= IFCLOCALPLACEMENT(${storeyLocalId},${cPlId});`);
    lines.push(`${cId}= IFCCOLUMN('${guid()}',${ownerHistoryId},'${col.name}','${col.material || ""}','IfcColumn',${cLocalId},$,$,.COLUMN.);`);
    columnIds.push(cId);
  }

  const beamIds: string[] = [];
  for (const beam of elements.beams) {
    const bId = getId();
    const bPlId = getId();
    const bAxId = getId();
    const bDrId = getId();
    const bOriginId = getId();
    const bLocalId = getId();
    lines.push(`${bOriginId}= IFCCARTESIANPOINT((0.,0.,0.));`);
    lines.push(`${bAxId}= IFCDIRECTION((0.,0.,1.));`);
    lines.push(`${bDrId}= IFCDIRECTION((1.,0.,0.));`);
    lines.push(`${bPlId}= IFCAXIS2PLACEMENT3D(${bOriginId},${bAxId},${bDrId});`);
    lines.push(`${bLocalId}= IFCLOCALPLACEMENT(${storeyLocalId},${bPlId});`);
    lines.push(`${bId}= IFCBEAM('${guid()}',${ownerHistoryId},'${beam.name}','${beam.material || ""}','IfcBeam',${bLocalId},$,$,.BEAM.);`);
    beamIds.push(bId);
  }

  const slabIds: string[] = [];
  for (const slab of elements.slabs) {
    const slId = getId();
    const slPlId = getId();
    const slAxId = getId();
    const slDrId = getId();
    const slOriginId = getId();
    const slLocalId = getId();
    lines.push(`${slOriginId}= IFCCARTESIANPOINT((0.,0.,0.));`);
    lines.push(`${slAxId}= IFCDIRECTION((0.,0.,1.));`);
    lines.push(`${slDrId}= IFCDIRECTION((1.,0.,0.));`);
    lines.push(`${slPlId}= IFCAXIS2PLACEMENT3D(${slOriginId},${slAxId},${slDrId});`);
    lines.push(`${slLocalId}= IFCLOCALPLACEMENT(${storeyLocalId},${slPlId});`);
    lines.push(`${slId}= IFCSLAB('${guid()}',${ownerHistoryId},'${slab.name}','${slab.material || ""}','IfcSlab',${slLocalId},$,$,.FLOOR.);`);
    slabIds.push(slId);
  }

  const allStoreyElements = [...spaceIds, ...wallIds, ...doorIds, ...windowIds, ...columnIds, ...beamIds, ...slabIds];

  const relContainedId = getId();
  if (allStoreyElements.length > 0) {
    lines.push(`${relContainedId}= IFCRELCONTAINEDINSPATIALSTRUCTURE('${guid()}',${ownerHistoryId},'Storey Elements',$,(${allStoreyElements.join(",")}),${storeyId});`);
  }

  const relAggrStoreyId = getId();
  lines.push(`${relAggrStoreyId}= IFCRELAGGREGATES('${guid()}',${ownerHistoryId},'Building Storeys',$,${buildingId},(${storeyId}));`);

  const relAggrBuildingId = getId();
  lines.push(`${relAggrBuildingId}= IFCRELAGGREGATES('${guid()}',${ownerHistoryId},'Site Buildings',$,${siteId},(${buildingId}));`);

  const relAggrSiteId = getId();
  lines.push(`${relAggrSiteId}= IFCRELAGGREGATES('${guid()}',${ownerHistoryId},'Project Sites',$,${projectId},(${siteId}));`);

  lines.push(`ENDSEC;`);
  lines.push(`END-ISO-10303-21;`);

  return lines.join("\n");
}
