using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using System.IO;
using System.Text.Json;

namespace Bsa.Revit;

public sealed record InventoryRequest(string DocumentPath, string ReportPath);

[Transaction(TransactionMode.ReadOnly)]
public sealed class InventoryCommand : IExternalCommand
{
    public Result Execute(ExternalCommandData data, ref string message, ElementSet elements)
    {
        try
        {
            using var dialog = new FileOpenDialog("JSON request (*.json)|*.json");
            if (dialog.Show() != ItemSelectionDialogResult.Confirmed) return Result.Cancelled;
            Run(data.Application, ModelPathUtils.ConvertModelPathToUserVisiblePath(dialog.GetSelectedModelPath()));
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = ex.Message;
            return Result.Failed;
        }
    }

    public static void Run(UIApplication app, string requestPath)
    {
        requestPath = Path.GetFullPath(requestPath);
        var root = new DirectoryInfo(Path.GetDirectoryName(requestPath)!);
        while (root != null && !(File.Exists(Path.Combine(root.FullName, "pyproject.toml"))
            && File.Exists(Path.Combine(root.FullName, "adapters/revit/Bsa.Revit.csproj")))) root = root.Parent;
        if (root == null) throw new ArgumentException("Request must reside inside the BSA repository");
        var requestBytes = File.ReadAllBytes(requestPath);
        var request = JsonSerializer.Deserialize<InventoryRequest>(System.Text.Encoding.UTF8.GetString(requestBytes).TrimStart('\uFEFF'))
            ?? throw new ArgumentException("Missing inventory request");
        string LocalPath(string value)
        {
            if (string.IsNullOrWhiteSpace(value) || !Path.IsPathFullyQualified(value))
                throw new ArgumentException("Absolute paths required");
            var path = Path.GetFullPath(value);
            if (!path.StartsWith(root.FullName + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("All artifacts must remain inside the repository");
            return path;
        }
        var expected = LocalPath(request.DocumentPath);
        var report = LocalPath(request.ReportPath);
        var doc = app.ActiveUIDocument?.Document ?? throw new InvalidOperationException("No active document");
        NativeInventory.CollectFromDocument(doc, expected, report, requestPath, requestBytes);
    }
}
