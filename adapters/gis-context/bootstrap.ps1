$ErrorActionPreference = "Stop"
$gisRepo = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$gisRuntime = Join-Path $gisRepo "tools/gis-runtime"
if (-not (Test-Path (Join-Path $gisRuntime "Scripts/python.exe"))) {
    & (Join-Path $gisRepo ".venv/Scripts/python.exe") -m venv $gisRuntime
    if ($LASTEXITCODE -ne 0) { throw "GIS environment creation failed" }
}
& (Join-Path $gisRuntime "Scripts/python.exe") -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "GIS dependency restore failed" }
