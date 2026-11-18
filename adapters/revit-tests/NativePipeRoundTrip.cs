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
    private sealed record ElbowConnection(int Pipe, int Fitting, XYZ PipeOrigin, XYZ FittingOrigin);

    [Test]
    public void CapturesSyntheticPipeInventory(Application application)
    {
        string source = SelectInput("BSA_REVIT_TEST_RVT", ".rvt");
        string sourceHash = Hash(source);
        string folder = Directory.CreateTempSubdirectory("bsa-revit-inventory-").FullName;
        string input = Path.Combine(folder, "input.rvt");
        string report = Path.Combine(folder, "inventory.json");
        File.Copy(source, input);
        VerifyFixtureBeforeOpen(input, sourceHash);
        var owned = application.OpenDocumentFile(input);
        try
        {
            Assert.That(owned.IsWorkshared || owned.IsLinked, Is.False);
            CaptureInventory(owned, input, report, sourceHash);
            using var inventory = JsonDocument.Parse(File.ReadAllBytes(report));
            var captured = inventory.RootElement;
            foreach (string field in new[] { "pipe_types", "system_types", "levels" })
                Assert.That(captured.GetProperty(field).GetArrayLength(), Is.GreaterThan(0), field);
            Assert.That(captured.GetProperty("saved_rvt_sha256").GetString(), Is.EqualTo(sourceHash));
            Console.WriteLine($"Copied RVT for request preparation: {input}");
            Console.WriteLine($"Copied RVT SHA-256: {sourceHash}");
            Console.WriteLine($"Native inventory: {report}");
            Console.WriteLine($"Native inventory SHA-256: {Hash(report)}");
        }
        finally
        {
            Assert.That(owned.Close(false), Is.True);
            Assert.That(Hash(source), Is.EqualTo(sourceHash));
            Assert.That(Hash(input), Is.EqualTo(sourceHash));
        }
    }

    [Test]
    public void CreatesAndReopensOnePipe(Application application)
    {
        var (request, source, sourceHash) = ReadFixtureRequest();

        string folder = Directory.CreateTempSubdirectory("bsa-revit-native-").FullName;
        string input = Path.Combine(folder, "input.rvt");
        string authored = Path.Combine(folder, "authored.rvt");
        File.Copy(source, input);
        VerifyFixtureBeforeOpen(input, sourceHash);
        Document? owned = null;
        try
        {
            owned = application.OpenDocumentFile(input);
            Assert.That(owned.IsWorkshared || owned.IsLinked, Is.False);
            var before = PipeIds(owned);
            VerifyRollback(owned, request with { DocumentPath = input }, before);
            Assert.That(owned.Close(false), Is.True);
            owned = null;
            Assert.That(Hash(input), Is.EqualTo(sourceHash));
            owned = application.OpenDocumentFile(input);
            var activeRequest = request with { DocumentPath = input };
            NativePipes.CreateInDocument(owned, activeRequest);
            var created = NewPipe(owned, before);
            string uniqueId = created.UniqueId;
            var expectedIds = before.Append(created.Id).ToHashSet();
            Assert.That(PipeIds(owned).SetEquals(expectedIds), Is.True);
            int[] connectorIds = VerifyPipe(owned, created, request);
            using (var options = new SaveAsOptions { OverwriteExistingFile = false })
                owned.SaveAs(authored, options);
            Assert.That(owned.Close(false), Is.True);
            owned = null;

            owned = application.OpenDocumentFile(authored);
            var reopened = owned.GetElement(uniqueId) as Pipe
                ?? throw new InvalidOperationException("Created pipe was missing after reopening the saved model");
            Assert.That(PipeIds(owned).SetEquals(expectedIds), Is.True);
            Assert.That(VerifyPipe(owned, reopened, request), Is.EqualTo(connectorIds));
            ElementProvenance.VerifyCommittedRequest(reopened, activeRequest);
            string authoredHash = Hash(authored);
            Assert.That(authoredHash, Is.Not.EqualTo(sourceHash));
            string reopenedReport = Path.Combine(folder, "reopened-inventory.json");
            CaptureInventory(owned, authored, reopenedReport, authoredHash);
            Console.WriteLine($"Saved and reopened synthetic RVT: {authored}");
            Console.WriteLine($"Saved RVT SHA-256: {authoredHash}");
            Console.WriteLine($"Reopened pipe UniqueId: {reopened.UniqueId}");
            Console.WriteLine($"Reopened inventory: {reopenedReport}");
            Console.WriteLine($"Reopened inventory SHA-256: {Hash(reopenedReport)}");
        }
        finally
        {
            if (owned is { IsValidObject: true })
                Assert.That(owned.Close(false), Is.True);
            Assert.That(Hash(source), Is.EqualTo(sourceHash));
        }
    }

    [Test]
    public void CapturesConnectedElbowAfterSavedReopen(Application application)
    {
        var (request, source, sourceHash) = ReadFixtureRequest();
        string folder = Directory.CreateTempSubdirectory("bsa-revit-elbow-").FullName;
        string input = Path.Combine(folder, "input.rvt");
        string authored = Path.Combine(folder, "elbow.rvt");
        File.Copy(source, input);
        VerifyFixtureBeforeOpen(input, sourceHash);
        Document? owned = null;
        try
        {
            owned = application.OpenDocumentFile(input);
            Assert.That(owned.IsWorkshared || owned.IsLinked, Is.False);
            var start = MetrePoint(request.StartMetres);
            var corner = MetrePoint(request.EndMetres);
            var leg = corner - start;
            Assert.That(Math.Abs(leg.Z), Is.LessThan(1e-7), "Use a horizontal synthetic first leg");
            var end = corner + new XYZ(-leg.Y, leg.X, 0);
            var pipeType = owned.GetElement(request.PipeTypeUniqueId) as PipeType;
            var systemType = owned.GetElement(request.SystemTypeUniqueId) as PipingSystemType;
            var level = owned.GetElement(request.LevelUniqueId) as Level;
            Assert.That(pipeType, Is.Not.Null);
            Assert.That(systemType, Is.Not.Null);
            Assert.That(level, Is.Not.Null);

            string firstId, secondId, fittingId;
            using (var transaction = new Transaction(owned, "BSA synthetic elbow control"))
            {
                Assert.That(transaction.Start(), Is.EqualTo(TransactionStatus.Started));
                transaction.SetFailureHandlingOptions(transaction.GetFailureHandlingOptions()
                    .SetFailuresPreprocessor(new NativePipes.RejectFailures()).SetClearAfterRollback(true));
                var first = Pipe.Create(owned, systemType!.Id, pipeType!.Id, level!.Id, start, corner);
                var second = Pipe.Create(owned, systemType.Id, pipeType.Id, level.Id, corner, end);
                double diameter = UnitUtils.ConvertToInternalUnits(request.DiameterMetres, UnitTypeId.Meters);
                foreach (var pipe in new[] { first, second })
                    Assert.That(pipe.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM).Set(diameter), Is.True);
                owned.Regenerate();
                var elbow = owned.Create.NewElbowFitting(EndAt(first, corner), EndAt(second, corner));
                (firstId, secondId, fittingId) = (first.UniqueId, second.UniqueId, elbow.UniqueId);
                Assert.That(transaction.Commit(), Is.EqualTo(TransactionStatus.Committed),
                    "Revit rejected the synthetic elbow transaction");
            }
            var connected = ElbowConnections(owned, firstId, secondId, fittingId);
            string expected = Path.Combine(folder, "expected-connections.json");
            var requiredPairs = connected.Select((pair, index) => new[] {
                new object[] { index == 0 ? firstId : secondId, pair.Pipe },
                new object[] { fittingId, pair.Fitting } }).ToArray();
            var positions = connected.SelectMany((pair, index) => new[] {
                new { port = requiredPairs[index][0], origin_m = OriginMetres(pair.PipeOrigin) },
                new { port = requiredPairs[index][1], origin_m = OriginMetres(pair.FittingOrigin) }
            }).ToArray();
            NativeEvidence.WriteJson(expected, new {
                source = "Synthetic elbow test: reciprocal physical connector pairs before save",
                required_pairs = requiredPairs, port_positions_m = positions });
            using (var options = new SaveAsOptions { OverwriteExistingFile = false })
                owned.SaveAs(authored, options);
            Assert.That(owned.Close(false), Is.True);
            owned = null;
            owned = application.OpenDocumentFile(authored);
            var reopenedConnections = ElbowConnections(owned, firstId, secondId, fittingId);
            foreach (var (before, after) in connected.Zip(reopenedConnections))
            {
                Assert.That((after.Pipe, after.Fitting), Is.EqualTo((before.Pipe, before.Fitting)));
                Assert.That(after.PipeOrigin.DistanceTo(before.PipeOrigin), Is.LessThanOrEqualTo(1e-7));
                Assert.That(after.FittingOrigin.DistanceTo(before.FittingOrigin), Is.LessThanOrEqualTo(1e-7));
            }
            string authoredHash = Hash(authored);
            string report = Path.Combine(folder, "reopened-inventory.json");
            CaptureInventory(owned, authored, report, authoredHash);
            Console.WriteLine($"Reopened elbow RVT: {authored} ({authoredHash})");
            var pairs = connected.Select((pair, index) => new {
                pipe_unique_id = index == 0 ? firstId : secondId, pipe_connector_id = pair.Pipe,
                fitting_unique_id = fittingId, fitting_connector_id = pair.Fitting });
            Console.WriteLine($"Saved pipe/fitting pairs: {JsonSerializer.Serialize(pairs)}");
            Console.WriteLine($"Pre-save expected connections: {expected} ({Hash(expected)})");
            Console.WriteLine($"Reopened inventory: {report} ({Hash(report)})");
        }
        finally
        {
            if (owned is { IsValidObject: true })
                Assert.That(owned.Close(false), Is.True);
            Assert.That(Hash(input), Is.EqualTo(sourceHash));
            Assert.That(Hash(source), Is.EqualTo(sourceHash));
        }
    }

    private static Connector EndAt(Pipe pipe, XYZ point) => pipe.ConnectorManager.Connectors.Cast<Connector>()
        .Single(port => port.ConnectorType == ConnectorType.End && port.Origin.DistanceTo(point) <= 1e-7);

    private static double[] OriginMetres(XYZ origin) => new[] { origin.X, origin.Y, origin.Z }
        .Select(value => UnitUtils.ConvertFromInternalUnits(value, UnitTypeId.Meters)).ToArray();

    private static ElbowConnection[] ElbowConnections(Document document, string firstId, string secondId, string fittingId)
    {
        var fitting = document.GetElement(fittingId) as FamilyInstance
            ?? throw new InvalidOperationException("Native elbow missing");
        Assert.That(fitting.Category.Id.Value, Is.EqualTo((long)BuiltInCategory.OST_PipeFitting));
        var result = new[] { firstId, secondId }.Select(id =>
        {
            var pipe = document.GetElement(id) as Pipe ?? throw new InvalidOperationException("Native pipe missing");
            var ends = pipe.ConnectorManager.Connectors.Cast<Connector>().ToArray();
            Assert.That(ends.Count(port => !port.IsConnected), Is.EqualTo(1));
            var end = ends.Single(port => port.IsConnected);
            var peer = end.AllRefs.Cast<Connector>().Single(port => port.Owner.Id != pipe.Id
                && port.ConnectorType != ConnectorType.Logical);
            Assert.That(peer.Owner.UniqueId, Is.EqualTo(fittingId));
            Assert.That(end.Domain, Is.EqualTo(Domain.DomainPiping));
            Assert.That(peer.Domain, Is.EqualTo(Domain.DomainPiping));
            Assert.That(peer.IsConnectedTo(end) && end.IsConnectedTo(peer), Is.True);
            Assert.That(peer.Origin.DistanceTo(end.Origin), Is.LessThanOrEqualTo(1e-7));
            return new ElbowConnection(end.Id, peer.Id, end.Origin, peer.Origin);
        }).ToArray();
        Assert.That(result[0].Fitting, Is.Not.EqualTo(result[1].Fitting));
        return result;
    }

    private static XYZ MetrePoint(double[] metres) => new(
        UnitUtils.ConvertToInternalUnits(metres[0], UnitTypeId.Meters),
        UnitUtils.ConvertToInternalUnits(metres[1], UnitTypeId.Meters),
        UnitUtils.ConvertToInternalUnits(metres[2], UnitTypeId.Meters));

    private static (PipeRequest Request, string Source, string SourceHash) ReadFixtureRequest()
    {
        string requestPath = SelectInput("BSA_REVIT_TEST_REQUEST", ".json");
        var request = JsonSerializer.Deserialize<PipeRequest>(File.ReadAllBytes(requestPath))
            ?? throw new InvalidOperationException("Missing pipe request");
        string source = Path.GetFullPath(request.DocumentPath);
        Assert.That(Path.GetDirectoryName(source), Is.EqualTo(Path.GetDirectoryName(requestPath)).IgnoreCase);
        Assert.That(Path.GetExtension(source), Is.EqualTo(".rvt").IgnoreCase);
        string sourceHash = Hash(source);
        Assert.That(sourceHash, Is.EqualTo(request.SavedRvtSha256).IgnoreCase);
        return (request, source, sourceHash);
    }

    private static void VerifyFixtureBeforeOpen(string input, string sourceHash)
    {
        Assert.That(Hash(input), Is.EqualTo(sourceHash), "Copied RVT differs from the selected fixture");
        using var info = BasicFileInfo.Extract(input);
        Assert.That(info.IsSavedInCurrentVersion, Is.True,
            $"Fixture was saved in Revit {info.Format}; use a fixture saved in the test host release");
        Assert.That(info.IsWorkshared, Is.False, "Use a standalone fixture for native regression");
    }

    private static void CaptureInventory(Document document, string model, string report, string modelHash)
    {
        string request = Path.ChangeExtension(report, "request.json");
        byte[] bytes = JsonSerializer.SerializeToUtf8Bytes(new { SavedRvtSha256 = modelHash });
        using (var stream = new FileStream(request, FileMode.CreateNew))
            stream.Write(bytes);
        NativeInventory.CollectFromDocument(document, model, report, request, bytes, modelHash);
    }

    private static string SelectInput(string variable, string extension)
    {
        string? path = Environment.GetEnvironmentVariable(variable);
        if (string.IsNullOrWhiteSpace(path) || !Path.IsPathFullyQualified(path)
            || !Path.GetExtension(path).Equals(extension, StringComparison.OrdinalIgnoreCase)
            || !File.Exists(path))
            throw new InvalidOperationException($"Select an absolute existing synthetic {extension} fixture in {variable}");
        return Path.GetFullPath(path);
    }

    private static HashSet<ElementId> PipeIds(Document document)
    {
        using var collector = new FilteredElementCollector(document);
        return collector.OfClass(typeof(Pipe)).ToElementIds().ToHashSet();
    }

    private static Pipe NewPipe(Document document, HashSet<ElementId> before)
    {
        using var collector = new FilteredElementCollector(document);
        return collector.OfClass(typeof(Pipe)).Cast<Pipe>().Single(pipe => !before.Contains(pipe.Id));
    }

    private static void VerifyRollback(Document document, PipeRequest request, HashSet<ElementId> before)
    {
        using var group = new TransactionGroup(document, "BSA native smoke test rollback control");
        Assert.That(group.Start(), Is.EqualTo(TransactionStatus.Started));
        string uniqueId;
        try
        {
            NativePipes.CreateInDocument(document, request);
            var created = NewPipe(document, before);
            uniqueId = created.UniqueId;
            ElementProvenance.VerifyCommittedRequest(created, request);
        }
        finally
        {
            Assert.That(group.RollBack(), Is.EqualTo(TransactionStatus.RolledBack));
        }
        Assert.That(document.GetElement(uniqueId), Is.Null);
        Assert.That(PipeIds(document).SetEquals(before), Is.True);
        ElementProvenance.RejectExistingRequest(document, request);
    }

    private static int[] VerifyPipe(Document document, Pipe pipe, PipeRequest request)
    {
        Assert.That(document.GetElement(pipe.GetTypeId()).UniqueId, Is.EqualTo(request.PipeTypeUniqueId));
        var system = pipe.get_Parameter(BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM).AsElementId();
        Assert.That(document.GetElement(system).UniqueId, Is.EqualTo(request.SystemTypeUniqueId));
        Assert.That(pipe.ReferenceLevel.UniqueId, Is.EqualTo(request.LevelUniqueId));
        Assert.That(UnitUtils.ConvertFromInternalUnits(pipe.Diameter, UnitTypeId.Meters),
            Is.EqualTo(request.DiameterMetres).Within(1e-8));
        var connectors = pipe.ConnectorManager.Connectors.Cast<Connector>().ToArray();
        Assert.That(connectors.Length, Is.EqualTo(2));
        return new[] { request.StartMetres, request.EndMetres }.Select(coordinates =>
        {
            var feet = coordinates.Select(value => UnitUtils.ConvertToInternalUnits(value, UnitTypeId.Meters)).ToArray();
            var point = new XYZ(feet[0], feet[1], feet[2]);
            var matches = connectors.Where(port => port.Domain == Domain.DomainPiping
                && port.ConnectorType == ConnectorType.End && port.Origin.DistanceTo(point) <= 1e-7).ToArray();
            Assert.That(matches.Length, Is.EqualTo(1));
            var connector = matches[0];
            Assert.That(connector.IsConnected, Is.False, "The single-pipe fixture expects an open physical end");
            Assert.That(connector.AllRefs.Cast<Connector>().Where(peer => peer.Owner.Id != pipe.Id
                && peer.ConnectorType != ConnectorType.Logical), Is.Empty, "Unexpected external physical peer");
            return connector.Id;
        }).ToArray();
    }

    private static string Hash(string path)
    {
        using var stream = File.OpenRead(path);
        return Convert.ToHexStringLower(SHA256.HashData(stream));
    }
}
