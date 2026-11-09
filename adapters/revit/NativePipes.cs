using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Plumbing;
using Autodesk.Revit.UI;
using System.IO;

namespace Bsa.Revit;

public sealed record PipeRequest(string DocumentPath, string Source,
    string PipeTypeUniqueId, string SystemTypeUniqueId, string LevelUniqueId,
    double[] StartMetres, double[] EndMetres, double DiameterMetres);

/// <summary>Invoke only in a valid Revit API context. No default engineering inputs.</summary>
public static class NativePipes
{
    public static object Create(UIApplication app, PipeRequest request)
    {
        Document doc = app.ActiveUIDocument?.Document
            ?? throw new InvalidOperationException("No active project");
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
        if (!double.IsFinite(request.DiameterMetres) || request.DiameterMetres <= 0)
            throw new ArgumentException("Positive finite diameter required");
        if (start.DistanceTo(end) <= Math.Max(doc.Application.ShortCurveTolerance, 1.0 / 120.0))
            throw new ArgumentException("Pipe is below Revit's minimum curve length");
        using var transaction = new Transaction(doc, "BSA: sourced native pipe");
        if (transaction.Start() != TransactionStatus.Started)
            throw new InvalidOperationException("Transaction did not start");
        transaction.SetFailureHandlingOptions(transaction.GetFailureHandlingOptions()
            .SetFailuresPreprocessor(new RejectFailures()).SetClearAfterRollback(true));
        try
        {
            var pipe = Pipe.Create(doc, systemType.Id, pipeType.Id, level.Id, start, end);
            var diameter = pipe.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM);
            if (diameter is null || diameter.IsReadOnly || !diameter.Set(Feet(request.DiameterMetres)))
                throw new InvalidOperationException("Native diameter could not be set");
            doc.Regenerate();
            var curve = ((LocationCurve)pipe.Location).Curve;
            if (Math.Abs(Metres(pipe.Diameter) - request.DiameterMetres) > 1e-8
                || curve.GetEndPoint(0).DistanceTo(start) > 1e-7
                || curve.GetEndPoint(1).DistanceTo(end) > 1e-7
                || pipe.ConnectorManager.Connectors.Size != 2)
                throw new InvalidOperationException("Native pipe readback differs from request");
            var result = new { unique_id = pipe.UniqueId, element_id = pipe.Id.Value.ToString(),
                source = request.Source, diameter_m = Metres(pipe.Diameter), length_m = Metres(curve.Length),
                connector_count = 2, saved = false, connected_system_verified = false, design_accepted = false };
            if (transaction.Commit() != TransactionStatus.Committed)
                throw new InvalidOperationException("Native transaction did not commit");
            return result;
        }
        catch
        {
            if (transaction.GetStatus() == TransactionStatus.Started) transaction.RollBack();
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
        return new XYZ(Feet(values[0]), Feet(values[1]), Feet(values[2]));
    }
}
