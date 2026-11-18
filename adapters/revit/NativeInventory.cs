using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Plumbing;
using System.IO;
using System.Security.Cryptography;
using System.Text.Json;

namespace Bsa.Revit;

internal static class NativeInventory
{
    internal static void CollectFromDocument(Document doc, string expected, string report,
        string requestPath, byte[] requestBytes)
    {
        if (doc.IsFamilyDocument || doc.IsModified || string.IsNullOrEmpty(doc.PathName)
            || !string.Equals(Path.GetFullPath(doc.PathName), expected, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Expected saved test project is not active, or has unsaved changes");
        if (Path.GetExtension(expected).ToLowerInvariant() != ".rvt"
            || Path.GetExtension(report).ToLowerInvariant() != ".json")
            throw new ArgumentException("Expected RVT model and JSON report");
        static string Hash(string path)
        {
            using var stream = File.OpenRead(path);
            return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
        }
        var before = Hash(expected);
        static double Metres(double value) => UnitUtils.ConvertFromInternalUnits(value, UnitTypeId.Meters);
        static double[] Point(XYZ p) => [Metres(p.X), Metres(p.Y), Metres(p.Z)];
        static object Named(Element e) => new { id = e.Id.Value.ToString(), unique_id = e.UniqueId, name = e.Name };
        static object ConnectorData(Connector c)
        {
            // Logical connectors do not support physical IsConnected/Origin queries.
            bool logical = c.ConnectorType == ConnectorType.Logical;
            return new
            {
                id = c.Id, domain = c.Domain.ToString(), connector_type = c.ConnectorType.ToString(),
                origin_m = logical ? null : Point(c.Origin),
                physically_connected = logical ? (bool?)null : c.IsConnected,
                references = c.AllRefs.Cast<Connector>().Where(r => r.Owner.Id != c.Owner.Id).Select(r =>
                {
                    bool referenceLogical = r.ConnectorType == ConnectorType.Logical;
                    return new
                    {
                        owner_unique_id = r.Owner.UniqueId, connector_id = r.Id,
                        connector_type = r.ConnectorType.ToString(), domain = r.Domain.ToString(),
                        origin_m = referenceLogical ? null : Point(r.Origin),
                        api_connected_to = c.IsConnectedTo(r),
                        reciprocal_reference = r.AllRefs.Cast<Connector>().Any(back =>
                            back.Owner.Id == c.Owner.Id && back.Id == c.Id),
                        separation_m = logical || referenceLogical ? (double?)null : Metres(c.Origin.DistanceTo(r.Origin))
                    };
                }).ToArray()
            };
        }
        var pipes = new FilteredElementCollector(doc).OfClass(typeof(Pipe)).Cast<Pipe>().Select(p => new
        {
            id = p.Id.Value.ToString(), unique_id = p.UniqueId, type_id = p.GetTypeId().Value.ToString(),
            type_unique_id = doc.GetElement(p.GetTypeId())?.UniqueId,
            system_type_unique_id = doc.GetElement(p.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM).AsElementId())?.UniqueId,
            level_unique_id = p.ReferenceLevel?.UniqueId,
            curve_kind = ((LocationCurve)p.Location).Curve.GetType().Name,
            endpoints_m = new[] { Point(((LocationCurve)p.Location).Curve.GetEndPoint(0)), Point(((LocationCurve)p.Location).Curve.GetEndPoint(1)) },
            system_unique_id = p.MEPSystem?.UniqueId, diameter_m = Metres(p.Diameter),
            length_m = Metres(((LocationCurve)p.Location).Curve.Length),
            creation_provenance = ElementProvenance.Read(p),
            connectors = p.ConnectorManager.Connectors.Cast<Connector>().Select(ConnectorData).ToArray()
        }).ToArray();
        var fittings = new FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_PipeFitting)
            .WhereElementIsNotElementType().Cast<FamilyInstance>().Select(f => new
            {
                id = f.Id.Value.ToString(), unique_id = f.UniqueId, type_id = f.GetTypeId().Value.ToString(),
                name = f.Name, connector_manager_available = f.MEPModel?.ConnectorManager != null,
                connectors = f.MEPModel?.ConnectorManager?.Connectors.Cast<Connector>().Select(ConnectorData).ToArray()
            }).ToArray();
        var result = new
        {
            scope = "Native pipe/fitting inventory with API physical flags, reciprocal references and separation; system acceptance pending",
            document_path = expected, saved_rvt_sha256 = before,
            request_sha256 = Convert.ToHexString(SHA256.HashData(requestBytes)).ToLowerInvariant(),
            adapter_sha256 = Hash(typeof(NativeInventory).Assembly.Location),
            revit_version = doc.Application.VersionNumber, units = "metres", pipes, fittings,
            connected_system_verified = false,
            pipe_types = new FilteredElementCollector(doc).OfClass(typeof(PipeType)).Select(Named).ToArray(),
            system_types = new FilteredElementCollector(doc).OfClass(typeof(PipingSystemType)).Select(Named).ToArray(),
            levels = new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>().Select(l => new
            { unique_id = l.UniqueId, name = l.Name, elevation_m = Metres(l.Elevation) }).ToArray(),
            design_accepted = false
        };
        var json = JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
        if (doc.IsModified || Hash(expected) != before || !File.ReadAllBytes(requestPath).SequenceEqual(requestBytes))
            throw new InvalidOperationException("Model or request changed during collection");
        // Existing reports are never overwritten; missing parent directories are not silently created.
        using var output = new FileStream(report, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        using var writer = new StreamWriter(output);
        writer.Write(json);
    }
}
