using ACadSharp.Entities;
using ACadSharp.IO;
using System.Security.Cryptography;
using System.Text.Json;

if (args.Length != 1 || !Path.GetExtension(args[0]).Equals(".dwg", StringComparison.OrdinalIgnoreCase))
{
    Console.Error.WriteLine("Usage: Bsa.DwgReadback <saved-drawing.dwg>");
    return 2;
}

try
{
    string path = Path.GetFullPath(args[0]);
    string readerPath = typeof(DwgReader).Assembly.Location;
    string readerHash = HashPath(readerPath);
    using var input = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
    string before = Hash(input);
    var document = DwgReader.Read(path);
    var entities = document.Entities.OrderBy(entity => entity.Handle).Select(entity => new
    {
        handle = entity.Handle.ToString("X"),
        type = entity.ObjectName,
        layer = entity.Layer.Name,
        geometry = Geometry(entity),
    }).ToArray();
    string output = JsonSerializer.Serialize(new
    {
        schema = "bsa.acadsharp-modelspace/1",
        source_sha256 = before,
        reader_version = "3.8.35",
        reader_sha256 = readerHash,
        insunits = (int)document.Header.InsUnits,
        entities,
        native_autocad_executed = false,
        design_accepted = false,
    });
    if (Hash(input) != before || HashPath(path) != before)
        throw new IOException("DWG changed during readback");
    if (HashPath(readerPath) != readerHash)
        throw new IOException("ACadSharp library changed during readback");
    Console.WriteLine(output);
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine($"{error.GetType().Name}: {error.Message}");
    return 2;
}

static string Hash(Stream input)
{
    input.Position = 0;
    return Convert.ToHexStringLower(SHA256.HashData(input));
}

static string HashPath(string path)
{
    using var input = File.OpenRead(path);
    return Hash(input);
}

static object? Geometry(Entity entity) => entity switch
{
    Arc arc => new
    {
        center = new[] { arc.Center.X, arc.Center.Y, arc.Center.Z },
        normal = new[] { arc.Normal.X, arc.Normal.Y, arc.Normal.Z },
        radius = arc.Radius,
        start_angle_rad = arc.StartAngle,
        end_angle_rad = arc.EndAngle,
    },
    Circle circle => new
    {
        center = new[] { circle.Center.X, circle.Center.Y, circle.Center.Z },
        normal = new[] { circle.Normal.X, circle.Normal.Y, circle.Normal.Z },
        radius = circle.Radius,
    },
    Line line => new
    {
        start = new[] { line.StartPoint.X, line.StartPoint.Y, line.StartPoint.Z },
        end = new[] { line.EndPoint.X, line.EndPoint.Y, line.EndPoint.Z },
        normal = new[] { line.Normal.X, line.Normal.Y, line.Normal.Z },
        thickness = line.Thickness,
    },
    Point point => new
    {
        location = new[] { point.Location.X, point.Location.Y, point.Location.Z },
    },
    Insert insert => new
    {
        block_name = insert.Block.Name,
        insert = new[] { insert.InsertPoint.X, insert.InsertPoint.Y, insert.InsertPoint.Z },
        normal = new[] { insert.Normal.X, insert.Normal.Y, insert.Normal.Z },
        scale = new[] { insert.XScale, insert.YScale, insert.ZScale },
        rotation_angle_rad = insert.Rotation,
        row_count = insert.RowCount,
        column_count = insert.ColumnCount,
        row_spacing = insert.RowSpacing,
        column_spacing = insert.ColumnSpacing,
    },
    TextEntity text => new
    {
        text = text.Value,
        insert = new[] { text.InsertPoint.X, text.InsertPoint.Y, text.InsertPoint.Z },
        height = text.Height,
        width_factor = text.WidthFactor,
        rotation_angle_rad = text.Rotation,
        oblique_angle_rad = text.ObliqueAngle,
        normal = new[] { text.Normal.X, text.Normal.Y, text.Normal.Z },
        horizontal_alignment = (int)text.HorizontalAlignment,
        vertical_alignment = (int)text.VerticalAlignment,
        alignment_point = (int)text.HorizontalAlignment == 0 && (int)text.VerticalAlignment == 0
            ? null : new[] { text.AlignmentPoint.X, text.AlignmentPoint.Y, text.AlignmentPoint.Z },
        style = text.Style.Name,
    },
    LwPolyline polyline => new
    {
        closed = polyline.IsClosed,
        elevation = polyline.Elevation,
        constant_width = polyline.ConstantWidth,
        normal = new[] { polyline.Normal.X, polyline.Normal.Y, polyline.Normal.Z },
        vertices = polyline.Vertices.Select(vertex => new[]
        {
            vertex.Location.X, vertex.Location.Y, vertex.StartWidth, vertex.EndWidth, vertex.Bulge,
        }).ToArray(),
    },
    _ => null,
};
