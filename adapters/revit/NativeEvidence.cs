using System.IO;
using System.Text.Json;

namespace Bsa.Revit;

internal static class NativeEvidence
{
    internal static void WriteJson<T>(string path, T value, JsonSerializerOptions? options = null)
    {
        string temporary = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(path))!,
            $".bsa-{Guid.NewGuid():N}.tmp");
        var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        try
        {
            using (stream)
            {
                JsonSerializer.Serialize(stream, value, options);
                stream.Flush(flushToDisk: true);
            }
            File.Move(temporary, path, overwrite: false);
        }
        finally
        {
            File.Delete(temporary);
        }
    }
}
