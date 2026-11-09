"""Read-only Revit API inventory. Load inside a valid Revit API context.

Call inventory(doc, expected_saved_path), then serialize its return value in the
host. No transactions, file writes, application startup or model edits occur.
Compatible syntax with IronPython 2.7; native execution remains to be verified.
"""
import os


def inventory(doc, expected_saved_path):
    if doc is None or not expected_saved_path:
        raise ValueError("An active document and explicit saved path are required")
    actual = doc.PathName
    if not actual or not os.path.isabs(expected_saved_path):
        raise ValueError("A saved local document and absolute expected path are required")
    if os.path.normcase(os.path.abspath(actual)) != os.path.normcase(os.path.abspath(expected_saved_path)):
        raise ValueError("Active document does not match expected path")
    if doc.IsFamilyDocument:
        raise ValueError("Expected a project, not a family document")

    from Autodesk.Revit.DB import FilteredElementCollector, Level, UnitUtils, UnitTypeId
    from Autodesk.Revit.DB.Plumbing import Pipe, PipeType, PipingSystemType

    def identity(element):
        return {"id": str(element.Id.Value), "unique_id": element.UniqueId}

    def metres(value):
        return UnitUtils.ConvertFromInternalUnits(value, UnitTypeId.Meters)

    def point(xyz):
        return [metres(xyz.X), metres(xyz.Y), metres(xyz.Z)]

    def named(element):
        from Autodesk.Revit.DB import Element
        row = identity(element)
        row["name"] = Element.Name.__get__(element)
        return row

    levels = []
    for level in FilteredElementCollector(doc).OfClass(Level):
        row = named(level)
        row["elevation_m"] = metres(level.Elevation)
        levels.append(row)
    pipes = []
    for pipe in FilteredElementCollector(doc).OfClass(Pipe):
        row = identity(pipe)
        row["type_id"] = str(pipe.GetTypeId().Value)
        row["length_m"] = metres(pipe.Location.Curve.Length)
        row["diameter_m"] = metres(pipe.Diameter)
        row["system_unique_id"] = pipe.MEPSystem.UniqueId if pipe.MEPSystem else None
        row["connectors"] = []
        for connector in pipe.ConnectorManager.Connectors:
            refs = []
            for other in connector.AllRefs:
                if other.Owner.Id == pipe.Id:
                    continue
                ref = identity(other.Owner)
                ref["connector_id"] = int(other.Id)
                ref["connector_type"] = str(other.ConnectorType)
                refs.append(ref)
            row["connectors"].append({
                "id": int(connector.Id), "origin_m": point(connector.Origin),
                "domain": str(connector.Domain), "connector_type": str(connector.ConnectorType),
                "references": refs,
            })
        pipes.append(row)
    return {
        "scope": "Native pipe inventory; references are not verified physical connectivity",
        "document_path": actual, "document_modified": bool(doc.IsModified),
        "revit_version": doc.Application.VersionNumber,
        "units": "metres", "levels": levels,
        "pipe_types": [named(x) for x in FilteredElementCollector(doc).OfClass(PipeType)],
        "system_types": [named(x) for x in FilteredElementCollector(doc).OfClass(PipingSystemType)],
        "pipes": pipes, "design_accepted": False,
    }
