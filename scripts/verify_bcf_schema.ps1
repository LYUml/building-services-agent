param(
    [Parameter(Mandatory)][string]$Archive,
    [Parameter(Mandatory)][string]$SchemaDirectory
)

$ErrorActionPreference = 'Stop'
$schemaRoot = (Resolve-Path -LiteralPath $SchemaDirectory).Path
$archivePath = (Resolve-Path -LiteralPath $Archive).Path
$pins = @{
    'extensions.xsd' = 'df9b49fc2368aba41cec8259fad266fe82d735b5319469834e7fe19bf0d83153'
    'markup.xsd' = '6c80f1c566ace8b405ae0ab530438aec2014bf35dd14cfc3c4cf0c5aa0b9d169'
    'project.xsd' = '44cf05c63fddcba335589cbbf5824458118561ffc23bb6c3e72a1f3217cce68a'
    'shared-types.xsd' = '93d20dfcc6d7f451ae85a8277559b0347478c278218a42f0ef41dcc5550a2090'
    'version.xsd' = 'cef0dcc112239457776cab33a5adeed0cf61c344e05bb5c6c4674c2df3643fa6'
    'visinfo.xsd' = '0855bc002310b4a9decd67b1b21631bd2e0368f0878183da8448e34d807e7418'
}
foreach ($name in $pins.Keys) {
    $path = Join-Path $schemaRoot $name
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $pins[$name]) {
        throw "Unexpected buildingSMART BCF 3.0 schema bytes for $name"
    }
}

$settings = @{}
foreach ($name in $pins.Keys | Where-Object { $_ -ne 'shared-types.xsd' }) {
    $schemaSet = [System.Xml.Schema.XmlSchemaSet]::new()
    $schemaSet.XmlResolver = [System.Xml.XmlUrlResolver]::new()
    $null = $schemaSet.Add($null, (Join-Path $schemaRoot $name))
    $schemaSet.Compile()
    $readerSettings = [System.Xml.XmlReaderSettings]::new()
    $readerSettings.Schemas = $schemaSet
    $readerSettings.ValidationType = [System.Xml.ValidationType]::Schema
    $readerSettings.ValidationFlags = [System.Xml.Schema.XmlSchemaValidationFlags]::ReportValidationWarnings
    $readerSettings.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
    $readerSettings.XmlResolver = $null
    $readerSettings.add_ValidationEventHandler({ param($sender, $event) throw $event.Exception })
    $settings[$name] = $readerSettings
}

$before = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
$zip = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
$documents = [System.Collections.Generic.Dictionary[string,System.Xml.XmlDocument]]::new(
    [StringComparer]::Ordinal)
try {
    foreach ($entry in $zip.Entries) {
        if (-not $entry.Name) { continue }
        $schemaName = switch -CaseSensitive -Regex ($entry.FullName) {
            '^bcf\.version$' { 'version.xsd'; break }
            '^project\.bcfp$' { 'project.xsd'; break }
            '^extensions\.xml$' { 'extensions.xsd'; break }
            '^[^/]+/markup\.bcf$' { 'markup.xsd'; break }
            '^[^/]+/[^/]+\.bcfv$' { 'visinfo.xsd'; break }
            default { throw "Archive member outside the generated IFC review format: $($entry.FullName)" }
        }
        if ($documents.ContainsKey($entry.FullName)) { throw "Repeated archive member: $($entry.FullName)" }
        $stream = $entry.Open()
        try {
            $reader = [System.Xml.XmlReader]::Create($stream, $settings[$schemaName])
            try {
                $document = [System.Xml.XmlDocument]::new()
                $document.XmlResolver = $null
                $document.Load($reader)
            } finally {
                $reader.Dispose()
            }
        } catch {
            throw "BCF XML failed schema validation for $($entry.FullName): $_"
        } finally {
            $stream.Dispose()
        }
        $documents.Add($entry.FullName, $document)
    }
} finally {
    $zip.Dispose()
}
foreach ($required in 'bcf.version', 'project.bcfp', 'extensions.xml') {
    if (-not $documents.ContainsKey($required)) { throw "Missing generated BCF archive member: $required" }
}
$referenced = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($entry in $documents.Keys | Where-Object { $_ -clike '*/markup.bcf' }) {
    $folder = $entry.Split('/')[0]
    $topic = $documents[$entry].SelectSingleNode('/Markup/Topic')
    if ($topic.GetAttribute('Guid') -cne $folder) {
        throw "BCF topic GUID differs from its archive folder: $entry"
    }
    foreach ($view in $topic.SelectNodes('Viewpoints/ViewPoint')) {
        $targetName = $view.SelectSingleNode('Viewpoint').InnerText
        if ($targetName -notmatch '^[^/\\:]+\.bcfv$') {
            throw "Invalid BCF viewpoint reference in $entry"
        }
        $target = "$folder/$targetName"
        if (-not $documents.ContainsKey($target) -or -not $referenced.Add($target)) {
            throw "Missing or repeated BCF viewpoint reference: $target"
        }
        if ($documents[$target].DocumentElement.GetAttribute('Guid') -cne $view.GetAttribute('Guid')) {
            throw "BCF viewpoint GUID differs from its markup reference: $target"
        }
    }
}
foreach ($entry in $documents.Keys | Where-Object { $_ -clike '*.bcfv' }) {
    if (-not $referenced.Contains($entry)) { throw "Unreferenced BCF viewpoint: $entry" }
}
if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -ne $before) {
    throw 'BCF archive changed during schema validation'
}
[ordered]@{
    archive_sha256 = $before
    schema_commit = '5834466b2477ac700d7a61990b4e67ec1005cc68'
    validated_xml_members = $documents.Count
    resolved_viewpoint_references = $referenced.Count
    schema_validation_pass = $true
} | ConvertTo-Json
