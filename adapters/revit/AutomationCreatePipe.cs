using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using DesignAutomationFramework;
using System.IO;
using System.Security.Cryptography;
using System.Text.Json;

namespace Bsa.Revit;

public sealed class AutomationCreatePipe : IExternalDBApplication
{
    public ExternalDBApplicationResult OnStartup(ControlledApplication application)
    {
        DesignAutomationBridge.DesignAutomationReadyEvent += CreateAndSave;
        return ExternalDBApplicationResult.Succeeded;
    }

    public ExternalDBApplicationResult OnShutdown(ControlledApplication application)
    {
        DesignAutomationBridge.DesignAutomationReadyEvent -= CreateAndSave;
        return ExternalDBApplicationResult.Succeeded;
    }

    private static void CreateAndSave(object? sender, DesignAutomationReadyEventArgs args)
    {
        args.Succeeded = false;
        var document = args.DesignAutomationData.RevitDoc
            ?? throw new InvalidOperationException("Automation did not supply a Revit document");
        if (document.IsWorkshared || document.IsLinked)
            throw new InvalidOperationException("Use a standalone non-workshared test RVT");
        string model = Path.GetFullPath("input.rvt");
        string requestPath = Path.GetFullPath("pipe-request.json");
        string output = Path.GetFullPath("authored.rvt");
        string receipt = Path.GetFullPath("creation.json");
        if (File.Exists(output) || File.Exists(receipt))
            throw new IOException("Automation requires fresh output paths");
        byte[] requestBytes = File.ReadAllBytes(requestPath);
        var request = JsonSerializer.Deserialize<PipeRequest>(requestBytes)
            ?? throw new ArgumentException("Missing pipe creation request");
        var created = NativePipes.CreateInDocument(document, request with { DocumentPath = model });
        using var options = new SaveAsOptions { OverwriteExistingFile = false };
        document.SaveAs(output, options);
        if (document.IsModified || !string.Equals(Path.GetFullPath(document.PathName), output, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("Revit did not report the expected saved document");
        var inputHash = HashFile(model);
        if (!string.Equals(inputHash, request.SavedRvtSha256, StringComparison.OrdinalIgnoreCase)
            || !File.ReadAllBytes(requestPath).SequenceEqual(requestBytes))
            throw new InvalidOperationException("Automation inputs changed during creation");
        var evidence = new
        {
            input_rvt_sha256 = inputHash,
            request_sha256 = Convert.ToHexString(SHA256.HashData(requestBytes)).ToLowerInvariant(),
            adapter_sha256 = HashFile(typeof(AutomationCreatePipe).Assembly.Location),
            saved_rvt_sha256 = HashFile(output),
            transaction_result = created,
            saved_reopen_verified = false,
            design_accepted = false,
        };
        using (var stream = new FileStream(receipt, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            JsonSerializer.Serialize(stream, evidence);
        args.Succeeded = true;
    }

    private static string HashFile(string path)
    {
        using var stream = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
    }
}
