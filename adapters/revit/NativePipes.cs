using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Plumbing;
using System.IO;
using System.Security.Cryptography;

namespace Bsa.Revit;

public sealed record PipeRequest(string DocumentPath, string Source,
    string PipeTypeUniqueId, string SystemTypeUniqueId, string LevelUniqueId,
    double[] StartMetres, double[] EndMetres, double DiameterMetres, string? SavedRvtSha256 = null);

/// <summary>Invoke only in a valid Revit API context. No default engineering inputs.</summary>
public static partial class NativePipes
{
    internal static object CreateInDocument(Document doc, PipeRequest request)
    {
        if (doc.IsFamilyDocument || doc.IsReadOnly || doc.IsModified || doc.IsModifiable)
            throw new InvalidOperationException("Use a saved, writable project without pending edits or transactions");
        if (!Path.IsPathFullyQualified(request.DocumentPath) || string.IsNullOrEmpty(doc.PathName)
            || !string.Equals(Path.GetFullPath(doc.PathName), Path.GetFullPath(request.DocumentPath), StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Active document path mismatch");
        if (string.IsNullOrWhiteSpace(request.Source))
            throw new ArgumentException("Explicit dimension/source basis required");
        var pipeType = doc.GetElement(request.PipeTypeUniqueId) as PipeType
            ?? throw new ArgumentException("Selected pipe type is not in this document");
        var systemType = doc.GetElement(request.SystemTypeUniqueId) as PipingSystemType
            ?? throw new ArgumentException("Selected piping system type is not in this document");
        var level = doc.GetElement(request.LevelUniqueId) as Level
            ?? throw new ArgumentException("Selected level is not in this document");
        var start = Point(request.StartMetres);
        var end = Point(request.EndMetres);
        var diameterFeet = Feet(request.DiameterMetres);
        if (!double.IsFinite(diameterFeet) || diameterFeet <= 0)
            throw new ArgumentException("Positive finite diameter required");
        if (start.DistanceTo(end) <= Math.Max(doc.Application.ShortCurveTolerance, 1.0 / 120.0))
            throw new ArgumentException("Pipe is below Revit's minimum curve length");
        ElementProvenance.RejectExistingRequest(doc, request);
        string currentHash;
        using (var savedModel = File.OpenRead(doc.PathName))
            currentHash = Convert.ToHexString(SHA256.HashData(savedModel));
        if (!string.Equals(currentHash, request.SavedRvtSha256, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Saved RVT hash mismatch; prepare a fresh request from a matching inventory");
        using var group = new TransactionGroup(doc, "BSA: create and verify native pipe");
        if (group.Start() != TransactionStatus.Started)
            throw new InvalidOperationException("Native pipe transaction group did not start");
        using var transaction = new Transaction(doc, "BSA: sourced native pipe");
        try
        {
            if (transaction.Start() != TransactionStatus.Started)
                throw new InvalidOperationException("Transaction did not start");
            transaction.SetFailureHandlingOptions(transaction.GetFailureHandlingOptions()
                .SetFailuresPreprocessor(new RejectFailures()).SetClearAfterRollback(true));
            var created = Pipe.Create(doc, systemType.Id, pipeType.Id, level.Id, start, end);
            var diameter = created.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM);
            if (diameter is null || diameter.IsReadOnly || !diameter.Set(diameterFeet))
                throw new InvalidOperationException("Native diameter could not be set");
            ElementProvenance.Attach(created, request);
            string uniqueId = created.UniqueId;
            if (transaction.Commit() != TransactionStatus.Committed)
                throw new InvalidOperationException("Native transaction did not commit");

            var pipe = doc.GetElement(uniqueId) as Pipe
                ?? throw new InvalidOperationException("Committed pipe could not be read back");
            var actualSystemTypeId = pipe.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)?.AsElementId();
            if (pipe.GetTypeId() != pipeType.Id || actualSystemTypeId != systemType.Id || pipe.ReferenceLevel?.Id != level.Id)
                throw new InvalidOperationException("Native pipe type, system type or reference level differs from request");
            if (pipe.Location is not LocationCurve location || location.Curve is not Line curve || !curve.IsBound)
                throw new InvalidOperationException("Committed pipe does not have a bounded straight centreline");
            if (!double.IsFinite(pipe.Diameter) || !double.IsFinite(curve.Length)
                || Math.Abs(curve.Length - start.DistanceTo(end)) > 1e-7
                || Math.Abs(Metres(pipe.Diameter) - request.DiameterMetres) > 1e-8
                || curve.GetEndPoint(0).DistanceTo(start) > 1e-7
                || curve.GetEndPoint(1).DistanceTo(end) > 1e-7)
                throw new InvalidOperationException("Native pipe readback differs from request");
            var connectors = pipe.ConnectorManager.Connectors.Cast<Connector>().ToArray();
            if (connectors.Length != 2 || connectors.Any(connector =>
                    connector.Domain != Domain.DomainPiping || connector.ConnectorType != ConnectorType.End)
                || connectors.Count(connector => connector.Origin.DistanceTo(start) <= 1e-7) != 1
                || connectors.Count(connector => connector.Origin.DistanceTo(end) <= 1e-7) != 1)
                throw new InvalidOperationException("Native piping end connectors differ from requested endpoints");
            ElementProvenance.VerifyCommittedRequest(pipe, request);
            var result = new { unique_id = pipe.UniqueId, element_id = pipe.Id.Value.ToString(),
                type_unique_id = pipeType.UniqueId, system_type_unique_id = systemType.UniqueId,
                level_unique_id = level.UniqueId,
                source = request.Source, diameter_m = Metres(pipe.Diameter), length_m = Metres(curve.Length),
                connector_count = connectors.Length,
                connectors = connectors.Select(connector => new {
                    id = connector.Id,
                    physically_connected = connector.IsConnected,
                    physical_references = connector.AllRefs.Cast<Connector>()
                        .Where(peer => peer.Owner.Id != pipe.Id && peer.ConnectorType != ConnectorType.Logical)
                        .Select(peer => new { owner_unique_id = peer.Owner.UniqueId, connector_id = peer.Id })
                        .ToArray(),
                    origin_m = new[] { Metres(connector.Origin.X), Metres(connector.Origin.Y), Metres(connector.Origin.Z) },
                }).ToArray(),
                saved = false, connected_system_verified = false, design_accepted = false };
            if (group.Assimilate() != TransactionStatus.Committed)
                throw new InvalidOperationException("Verified pipe transaction group did not commit");
            return result;
        }
        catch (Exception error)
        {
            if (transaction.GetStatus() == TransactionStatus.Started) transaction.RollBack();
            if (group.GetStatus() == TransactionStatus.Started && group.RollBack() != TransactionStatus.RolledBack)
                throw new InvalidOperationException("Native pipe transaction group rollback could not be confirmed", error);
            throw;
        }
    }

    private static double Feet(double metres) => UnitUtils.ConvertToInternalUnits(metres, UnitTypeId.Meters);
    private sealed class RejectFailures : IFailuresPreprocessor
    {
        public FailureProcessingResult PreprocessFailures(FailuresAccessor accessor) =>
            accessor.GetFailureMessages().Count > 0
                ? FailureProcessingResult.ProceedWithRollBack : FailureProcessingResult.Continue;
    }
    private static double Metres(double feet) => UnitUtils.ConvertFromInternalUnits(feet, UnitTypeId.Meters);
    private static XYZ Point(double[] values)
    {
        if (values is null || values.Length != 3 || values.Any(x => !double.IsFinite(x)))
            throw new ArgumentException("Three finite metre coordinates required");
        var feet = values.Select(Feet).ToArray();
        if (feet.Any(value => !double.IsFinite(value)))
            throw new ArgumentException("Pipe endpoint is outside Revit coordinate limits");
        var point = new XYZ(feet[0], feet[1], feet[2]);
        if (!XYZ.IsWithinLengthLimits(point))
            throw new ArgumentException("Pipe endpoint is outside Revit coordinate limits");
        return point;
    }
}
