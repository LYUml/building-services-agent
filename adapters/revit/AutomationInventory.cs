using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using DesignAutomationFramework;
using System.IO;
using System.Text.Json;

namespace Bsa.Revit;

public sealed class AutomationInventory : IExternalDBApplication
{
    private sealed record Request(string SavedRvtSha256);

    public ExternalDBApplicationResult OnStartup(ControlledApplication application)
    {
        DesignAutomationBridge.DesignAutomationReadyEvent += Collect;
        return ExternalDBApplicationResult.Succeeded;
    }

    public ExternalDBApplicationResult OnShutdown(ControlledApplication application)
    {
        DesignAutomationBridge.DesignAutomationReadyEvent -= Collect;
        return ExternalDBApplicationResult.Succeeded;
    }

    private static void Collect(object? sender, DesignAutomationReadyEventArgs args)
    {
        args.Succeeded = false;
        var document = args.DesignAutomationData.RevitDoc
            ?? throw new InvalidOperationException("Automation did not supply a Revit document");
        string model = Path.GetFullPath("input.rvt");
        string requestPath = Path.GetFullPath("inventory-request.json");
        string output = Path.GetFullPath("inventory.json");
        byte[] requestBytes = File.ReadAllBytes(requestPath);
        var request = JsonSerializer.Deserialize<Request>(requestBytes);
        string? hash = request?.SavedRvtSha256;
        if (hash is null || hash.Length != 64 || !hash.All(Uri.IsHexDigit))
            throw new ArgumentException("An explicit saved RVT SHA-256 is required");
        NativeInventory.CollectFromDocument(document, model, output, requestPath, requestBytes, hash);
        args.Succeeded = true;
    }
}
