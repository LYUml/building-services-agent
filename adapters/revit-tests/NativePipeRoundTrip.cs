using System.Security.Cryptography;
using System.Text.Json;
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Plumbing;
using Bsa.Revit;
using NUnit.Framework;

namespace Bsa.Revit.NativeTests;

public sealed class NativePipeRoundTrip
{
    [Test]
    public void CreatesAndReopensOnePipe(Application application)
    {
        string? selected = Environment.GetEnvironmentVariable("BSA_REVIT_TEST_REQUEST");
        if (string.IsNullOrWhiteSpace(selected) || !Path.IsPathFullyQualified(selected))
            throw new InvalidOperationException("Select an absolute prepared synthetic request in BSA_REVIT_TEST_REQUEST");
        string requestPath = Path.GetFullPath(selected);
        var request = JsonSerializer.Deserialize<PipeRequest>(File.ReadAllBytes(requestPath))
            ?? throw new InvalidOperationException("Missing pipe request");
        string source = Path.GetFullPath(request.DocumentPath);
        Assert.That(Path.GetDirectoryName(source), Is.EqualTo(Path.GetDirectoryName(requestPath)).IgnoreCase);
        Assert.That(Path.GetExtension(source), Is.EqualTo(".rvt").IgnoreCase);
        string sourceHash = Hash(source);
        Assert.That(sourceHash, Is.EqualTo(request.SavedRvtSha256).IgnoreCase);

        string folder = Directory.CreateTempSubdirectory("bsa-revit-native-").FullName;
        string input = Path.Combine(folder, "input.rvt");
        string authored = Path.Combine(folder, "authored.rvt");
        File.Copy(source, input);
        Document? owned = null;
        try
        {
            owned = application.OpenDocumentFile(input);
            Assert.That(owned.IsWorkshared || owned.IsLinked, Is.False);
            var before = new FilteredElementCollector(owned).OfClass(typeof(Pipe)).ToElementIds().ToHashSet();
            NativePipes.CreateInDocument(owned, request with { DocumentPath = input });
            var created = new FilteredElementCollector(owned).OfClass(typeof(Pipe)).Cast<Pipe>()
                .Where(pipe => !before.Contains(pipe.Id)).Single();
            string uniqueId = created.UniqueId;
            VerifyPipe(owned, created, request);
            using (var options = new SaveAsOptions { OverwriteExistingFile = false })
                owned.SaveAs(authored, options);
            Assert.That(owned.Close(false), Is.True);
            owned = null;

            owned = application.OpenDocumentFile(authored);
            var reopened = owned.GetElement(uniqueId) as Pipe
                ?? throw new InvalidOperationException("Created pipe was missing after reopening the saved model");
            VerifyPipe(owned, reopened, request);
            TestContext.WriteLine($"Saved and reopened synthetic RVT: {authored}");
            TestContext.WriteLine($"Saved RVT SHA-256: {Hash(authored)}");
        }
        finally
        {
            if (owned is { IsValidObject: true })
                Assert.That(owned.Close(false), Is.True);
            Assert.That(Hash(source), Is.EqualTo(sourceHash));
        }
    }

    private static void VerifyPipe(Document document, Pipe pipe, PipeRequest request)
    {
        Assert.That(document.GetElement(pipe.GetTypeId()).UniqueId, Is.EqualTo(request.PipeTypeUniqueId));
        var system = pipe.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM).AsElementId();
        Assert.That(document.GetElement(system).UniqueId, Is.EqualTo(request.SystemTypeUniqueId));
        Assert.That(pipe.ReferenceLevel.UniqueId, Is.EqualTo(request.LevelUniqueId));
        Assert.That(UnitUtils.ConvertFromInternalUnits(pipe.Diameter, UnitTypeId.Meters),
            Is.EqualTo(request.DiameterMetres).Within(1e-8));
        var connectors = pipe.ConnectorManager.Connectors.Cast<Connector>().ToArray();
        Assert.That(connectors.Length, Is.EqualTo(2));
        foreach (var coordinates in new[] { request.StartMetres, request.EndMetres })
        {
            var feet = coordinates.Select(value => UnitUtils.ConvertToInternalUnits(value, UnitTypeId.Meters)).ToArray();
            var point = new XYZ(feet[0], feet[1], feet[2]);
            Assert.That(connectors.Count(port => port.Domain == Domain.DomainPiping
                && port.ConnectorType == ConnectorType.End && port.Origin.DistanceTo(point) <= 1e-7), Is.EqualTo(1));
        }
    }

    private static string Hash(string path)
    {
        using var stream = File.OpenRead(path);
        return Convert.ToHexStringLower(SHA256.HashData(stream));
    }
}
