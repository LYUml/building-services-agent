using Autodesk.Revit.DB;
using Autodesk.Revit.DB.ExtensibleStorage;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Bsa.Revit;

/// <summary>Creation-request history, not proof of present geometry or source validity.</summary>
public static class ElementProvenance
{
    private static readonly Guid SchemaId = new("93703c6b-6f5f-41ed-a86e-aa38986a445f");
    private const string SchemaName = "BsaCreationRequestV1";
    private const string FieldName = "PayloadJson";
    private sealed record Payload(int Version, string ElementUniqueId, string RequestJson, string RequestSha256);

    private static string Hash(string text) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(text))).ToLowerInvariant();

    private static void CheckSchema(Schema schema)
    {
        if (schema.SchemaName != SchemaName || schema.GetField(FieldName)?.ValueType != typeof(string)
            || schema.ListFields().Count != 1)
            throw new InvalidOperationException("BSA provenance schema identity conflicts with installed schema");
    }

    public static void Attach(Element element, PipeRequest request)
    {
        if (!element.Document.IsModifiable)
            throw new InvalidOperationException("Provenance must be attached inside the creation transaction");
        var schema = Schema.Lookup(SchemaId);
        if (schema == null)
        {
            var builder = new SchemaBuilder(SchemaId);
            builder.SetSchemaName(SchemaName);
            builder.SetDocumentation("BSA original creation request; not current-state or engineering acceptance");
            builder.SetReadAccessLevel(AccessLevel.Public);
            builder.SetWriteAccessLevel(AccessLevel.Public);
            builder.AddSimpleField(FieldName, typeof(string));
            schema = builder.Finish();
        }
        CheckSchema(schema);
        if (element.GetEntity(schema).IsValid())
            throw new InvalidOperationException("Existing creation provenance must not be overwritten");
        string requestJson = JsonSerializer.Serialize(request);
        string payloadJson = JsonSerializer.Serialize(new Payload(1, element.UniqueId, requestJson, Hash(requestJson)));
        var entity = new Entity(schema);
        entity.Set(schema.GetField(FieldName), payloadJson);
        element.SetEntity(entity);
        if (element.GetEntity(schema).Get<string>(schema.GetField(FieldName)) != payloadJson)
            throw new InvalidOperationException("Creation provenance readback failed");
    }

    public static object? Read(Element element)
    {
        var schema = Schema.Lookup(SchemaId);
        if (schema == null) return null;
        CheckSchema(schema);
        var entity = element.GetEntity(schema);
        if (!entity.IsValid()) return null;
        var payload = JsonSerializer.Deserialize<Payload>(entity.Get<string>(schema.GetField(FieldName)))
            ?? throw new InvalidOperationException("Empty BSA provenance payload");
        if (payload.Version != 1 || string.IsNullOrWhiteSpace(payload.RequestJson)
            || Hash(payload.RequestJson) != payload.RequestSha256)
            throw new InvalidOperationException("Invalid BSA creation-request integrity");
        var request = JsonSerializer.Deserialize<PipeRequest>(payload.RequestJson)
            ?? throw new InvalidOperationException("Missing stored creation request");
        return new
        {
            schema_version = payload.Version, original_element_unique_id = payload.ElementUniqueId,
            element_identity_matches = payload.ElementUniqueId == element.UniqueId,
            creation_request = request, request_sha256 = payload.RequestSha256,
            source_verified = false, current_geometry_matches_request = (bool?)null,
            scope = "Original request history only; copying may duplicate metadata; hash is not authentication"
        };
    }
}
