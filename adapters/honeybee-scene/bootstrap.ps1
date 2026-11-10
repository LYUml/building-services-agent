$ErrorActionPreference = "Stop"
$sceneRepo = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$sceneRuntime = Join-Path $sceneRepo "tools/honeybee-scene-runtime"
if (-not (Test-Path (Join-Path $sceneRuntime "Scripts/python.exe"))) {
    & (Join-Path $sceneRepo ".venv/Scripts/python.exe") -m venv $sceneRuntime
    if ($LASTEXITCODE -ne 0) { throw "Scene runtime creation failed" }
}
& (Join-Path $sceneRuntime "Scripts/python.exe") -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Scene dependency restore failed" }
