param([Parameter(Mandatory=$true)][string]$Model, [Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$target = [IO.Path]::GetFullPath((Join-Path (Get-Location) $Out))
$modelPath = [IO.Path]::GetFullPath((Join-Path (Get-Location) $Model))
foreach ($candidate in @($target,$modelPath)) {
    if (-not $candidate.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Model and output must remain inside the repository.'
    }
}
if ([IO.Path]::GetExtension($modelPath) -ine '.rvt') { throw 'Expected an RVT model.' }
if (Test-Path -LiteralPath $target) { throw 'Choose a new output directory.' }
$assembly = Join-Path $repoRoot 'adapters/revit/bin/Release/net10.0-windows/Bsa.Revit.dll'
if (-not (Test-Path -LiteralPath $assembly -PathType Leaf)) { throw 'Build the adapter first.' }
[IO.Directory]::CreateDirectory($target) | Out-Null
$xml = [xml]'<RevitAddIns><AddIn Type="Command"><Assembly/><AddInId>257a2a29-5b53-4e6a-a56a-62e96348812e</AddInId><FullClassName>Bsa.Revit.InventoryCommand</FullClassName><Text>BSA Read-only Pipe Inventory</Text><VendorId>BSAG</VendorId><VendorDescription>Building Services Agent development</VendorDescription><VisibilityMode>NotVisibleWhenNoActiveDocument</VisibilityMode></AddIn></RevitAddIns>'
$xml.RevitAddIns.AddIn.Assembly = $assembly
$xml.Save((Join-Path $target 'Bsa.Inventory.addin'))
@{DocumentPath=$modelPath;ReportPath=(Join-Path $target 'inventory.json')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $target 'request.json') -Encoding utf8
@{scope='Prepared only; no registration, application restart or native command execution';assembly=$assembly;assembly_sha256=(Get-FileHash -LiteralPath $assembly -Algorithm SHA256).Hash.ToLowerInvariant();native_executed=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $target 'preparation.json') -Encoding utf8
Write-Output $target
