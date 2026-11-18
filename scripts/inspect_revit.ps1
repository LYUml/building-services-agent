param(
    [Parameter(Mandatory=$true)][string]$Out,
    [string]$Adapter
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$target = [IO.Path]::GetFullPath((Join-Path (Get-Location) $Out))
if (-not $target.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Output must remain inside the repository.'
}
if (Test-Path -LiteralPath $target) { throw 'Choose a new output file.' }
$autodesk = Join-Path $env:ProgramFiles 'Autodesk'
$revit = Join-Path $autodesk 'Revit 2027'
$consolePath = Join-Path $revit 'RevitCoreConsole.exe'
$files = @('Revit.exe','RevitAPI.dll','RevitAPIUI.dll') | ForEach-Object {
    $path = Join-Path $revit $_
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $file = Get-Item -LiteralPath $path
        [ordered]@{name=$_;path=$path;file_version=$file.VersionInfo.FileVersion;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
    }
}
$servers = @('Read','Write','Experimental') | ForEach-Object {
    $path = Join-Path $autodesk "Revit 2027 MCP Server $_-Tools Technical Preview/Autodesk.RevitMcpServer.Stdio.exe"
    [ordered]@{configuration=$_;documented_path=$path;exists=(Test-Path -LiteralPath $path -PathType Leaf)}
}
$dynamoPath = Join-Path $revit 'AddIns/DynamoForRevit/Built-In packages/packages/DynamoMCP/pkg.json'
$dynamo = $null
if (Test-Path -LiteralPath $dynamoPath) {
    $package = Get-Content -LiteralPath $dynamoPath -Raw | ConvertFrom-Json
    $dynamo = [ordered]@{name=$package.name;version=$package.version;engine_version=$package.engine_version;metadata_sha256=(Get-FileHash -LiteralPath $dynamoPath).Hash.ToLowerInvariant()}
}
$runtimePath = Join-Path $revit 'RevitAPI.runtimeconfig.json'
$runtime = $null
if (Test-Path -LiteralPath $runtimePath -PathType Leaf) {
    $runtimeConfig = Get-Content -LiteralPath $runtimePath -Raw | ConvertFrom-Json
    $runtime = [ordered]@{tfm=$runtimeConfig.runtimeOptions.tfm;frameworks=@($runtimeConfig.runtimeOptions.frameworks);sha256=(Get-FileHash -LiteralPath $runtimePath -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$assemblyPath = Join-Path $repoRoot 'adapters/revit/bin/Release/net10.0-windows/Bsa.Revit.dll'
if ($Adapter) {
    $assemblyPath = (Resolve-Path -LiteralPath $Adapter).ProviderPath
    if (-not $assemblyPath.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetExtension($assemblyPath) -ne '.dll' -or -not (Test-Path -LiteralPath $assemblyPath -PathType Leaf)) {
        throw 'Select a repository-local adapter DLL.'
    }
}
$assembly = $null
if (Test-Path -LiteralPath $assemblyPath -PathType Leaf) {
    $assembly = [ordered]@{
        path=$assemblyPath
        sha256=(Get-FileHash -LiteralPath $assemblyPath -Algorithm SHA256).Hash.ToLowerInvariant()
        authenticode_status=(Get-AuthenticodeSignature -LiteralPath $assemblyPath).Status.ToString()
        host_policy_acceptance_verified=$false
    }
}
$result = [ordered]@{
    scope='Read-only installation inventory; no application launch, licence check, MCP connection or model access'
    inspected_at_utc=[DateTime]::UtcNow.ToString('o')
    revit_files=@($files)
    api_runtime=$runtime
    desktop_core_console=[ordered]@{
        checked_path=$consolePath
        exists=(Test-Path -LiteralPath $consolePath -PathType Leaf)
        execution_verified=$false
    }
    public_mcp_documented_locations=@($servers)
    dynamo_mcp=$dynamo
    local_release_adapter=$assembly
    revit_process_ids=@(Get-Process -Name Revit -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
    connection_verified=$false
    document_access_verified=$false
    design_accepted=$false
}
[IO.Directory]::CreateDirectory((Split-Path -Parent $target)) | Out-Null
$json = $result | ConvertTo-Json -Depth 6
$bytes = [Text.Encoding]::UTF8.GetBytes($json + [Environment]::NewLine)
$stream = [IO.File]::Open($target, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
try { $stream.Write($bytes, 0, $bytes.Length) }
finally { $stream.Dispose() }
Write-Output $target
