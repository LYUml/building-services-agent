using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using System.IO;
using System.Text.Json;

namespace Bsa.Revit;

/// <summary>Explicit single-pipe test command; never opens or saves a document.</summary>
[Transaction(TransactionMode.Manual)]
public sealed class CreatePipeCommand : IExternalCommand
{
    public Result Execute(ExternalCommandData data, ref string message, ElementSet elements)
    {
        try
        {
            using var dialog = new FileOpenDialog("Pipe request (*.json)|*.json");
            if (dialog.Show() != ItemSelectionDialogResult.Confirmed) return Result.Cancelled;
            var result = Run(data.Application, ModelPathUtils.ConvertModelPathToUserVisiblePath(dialog.GetSelectedModelPath()));
            Autodesk.Revit.UI.TaskDialog.Show("BSA native pipe created — not saved", JsonSerializer.Serialize(result,
                new JsonSerializerOptions { WriteIndented = true }));
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = ex.Message;
            return Result.Failed;
        }
    }

    public static object Run(UIApplication app, string requestPath)
    {
        requestPath = Path.GetFullPath(requestPath);
        var root = new DirectoryInfo(Path.GetDirectoryName(requestPath)!);
        while (root != null && !(File.Exists(Path.Combine(root.FullName, "pyproject.toml"))
            && File.Exists(Path.Combine(root.FullName, "adapters/revit/Bsa.Revit.csproj")))) root = root.Parent;
        if (root == null) throw new ArgumentException("Request must be inside the BSA repository");
        using var requestFile = new FileStream(requestPath, FileMode.Open, FileAccess.Read, FileShare.Read);
        using var reader = new StreamReader(requestFile, System.Text.Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        // PowerShell-authored UTF-8 JSON may include a BOM.
        var text = reader.ReadToEnd();
        var request = JsonSerializer.Deserialize<PipeRequest>(text)
            ?? throw new ArgumentException("Missing pipe request");
        if (!Path.IsPathFullyQualified(request.DocumentPath)
            || !Path.GetFullPath(request.DocumentPath).StartsWith(root.FullName + Path.DirectorySeparatorChar,
                StringComparison.OrdinalIgnoreCase)
            || !string.Equals(Path.GetExtension(request.DocumentPath), ".rvt", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Expected an explicit repository-local test RVT");
        // Hold the request read-only through the transaction. NativePipes
        // revalidates the active document immediately before starting it.
        return NativePipes.Create(app, request);
    }
}
