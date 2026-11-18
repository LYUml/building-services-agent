using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace Bsa.Revit;

public static partial class NativePipes
{
    public static object Create(UIApplication app, PipeRequest request)
    {
        Document doc = app.ActiveUIDocument?.Document
            ?? throw new InvalidOperationException("No active project");
        return CreateInDocument(doc, request);
    }
}
