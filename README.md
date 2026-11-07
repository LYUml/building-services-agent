# Building Services Agent

需求文档 → 可追溯项目数据 → CAD/BIM → 工程计算与仿真 → 校核 → 交付。

An agent workspace and deterministic engineering tools for reusable MEP workflows. The AI reads requirements and orchestrates tools; calculation engines compute results. Unknown inputs stay unknown.

## Run the first vertical slice

```powershell
.venv/Scripts/python -m pip install -e .
bsa validate examples/office-electrical/project.json
bsa run examples/office-electrical/project.json --out runs/office
.venv/Scripts/python -m unittest discover -s tests -v
```

The synthetic office example produces traceable circuit calculations, an editable DXF device overlay, a drawing preview, an HTML report, and input/output hashes. It is a demonstration, not the completed coursework or a certified design. No old project files are copied or modified.

## Use with an agent

Open this repository as the workspace. Ask the agent to use `$building-services-design` with your brief and original drawings. Project skills are in `.agents/skills`. The intake skill creates a requirement matrix before design; domain skills select the appropriate authoring and analysis tools. This repository uses the host agent's reasoning; it does not require or hide a separate paid model API.

## Current evidence and limits

The first slice implements electrical load aggregation, design current and conditional cable/protection/voltage-drop checks, plus a DXF overlay. Cable ampacity, factors, mV/A/m and limits are explicit sourced inputs, not embedded regulation tables. Fault disconnection, breaking capacity, selectivity and lighting photometry are not yet calculated. Reports keep these pending; a successful CLI run is not full design acceptance.

Native conversion of synthetic CIRCLE/TEXT overlays now has a tested AutoCAD 2027 adapter; existing-bottom-drawing integration, BIM authoring, energy simulation and other MEP domains remain work in progress. See [roadmap](docs/ROADMAP.md), [project format](docs/PROJECT_FORMAT.md), and [upstream attribution](THIRD_PARTY.md). No upstream implementation has been copied into this initial milestone.

## Native AutoCAD example

```powershell
.venv/Scripts/python -m bsa.native_cad runs/office/devices.dxf --out runs/native-office
$env:BSA_TEST_AUTOCAD='1'
.venv/Scripts/python -m unittest discover -s tests -v
```

Requires a licensed local AutoCAD 2027 installation at the default path (or pass `--exe`). Core Console runs on generated copies in isolated processes, never attaching to the GUI session. The adapter saves DWG, reopens it in a second process, checks CIRCLE/TEXT geometry, layers, labels and metre units, then plots a padded fit-to-page PDF. It refuses output overwrite. `native-verification.json` keeps visual review pending until a separate actual image inspection is recorded. This restricted overlay workflow does not yet merge existing base drawings, produce fixed-scale sheets or validate all CAD entity types.

## Real energy-engine example

```powershell
.venv/Scripts/python scripts/setup_energy.py
.venv/Scripts/python -m bsa.energy examples/two-zone-energy/project.json --out runs/energy --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python scripts/probe_openstudio_mcp.py runs/energy/baseline/model.osm
```

Bootstrap is Windows x64 only, verifies the portable engine archive checksum and uses an inspected upstream MCP commit. It changes only this workspace. `pip install -e ".[energy]"` installs the optional SDK when an engine is already available.

The current energy adapter is a two-zone design-day workflow: OSM + IDF creation, shared-wall matching, real EnergyPlus execution, SQL results and baseline/variant comparison. All example inputs are synthetic. It reports coincident thermal peaks and simulated-period quantities separately from lighting electricity. It does **not** report annual kWh, EUI, plant electricity or a finished HVAC layout. Original input and engine/artifact hashes, translation warnings and simulation logs are retained. The MCP probe exercises upstream model reading; it does not claim upstream simulation execution.

## Brief-to-tools workflow

Use `python -m bsa.workflow intake <brief.md> --out <new-intake.json>` to index source passages. The host AI then creates a quoted, source-linked plan and project data. `validate` checks the handoff; `execute` dispatches electrical/native-CAD/energy tasks and creates an evidence matrix; `verify` detects changed inputs or task artifacts. See [workflow contract and runnable combined example](docs/WORKFLOWS.md). The combined example has been executed against actual AutoCAD and EnergyPlus. Manual review remains pending, so it is not an accepted final design.

## PDF and Word requirements

[Document intake](docs/DOCUMENT_INTAKE.md) supports PDF page locators, Word body/table/header/note locators and optional offline OCR. Extraction gaps remain visible and require source review. Scanned/outlined text can be OCR-indexed, but recognition is never silently accepted as engineering data.

## Editable IFC MEP models

[IFC authoring](docs/IFC_MODELS.md) creates source-linked IFC4 spaces, device envelopes, distribution-system membership and directed port connections. Electrical and ventilation examples have been generated, reopened and checked through the geometry engine and schema/EXPRESS validator. Use the `bim` workflow adapter or `python -m bsa.bim`. Detailed product geometry, physical routing and engineering acceptance remain pending.

## Duct and pipe pressure analysis

[Network calculations](docs/NETWORKS.md) aggregate prescribed flow through circular tree networks and report friction, fittings, elevation, residual total pressure and the critical path. The `network` workflow adapter has air and water examples with independent formula tests. Loops, operating-point selection, physical routing and domain compliance remain outside this adapter.

## Shared electrical data

[Coordinated generation](docs/COORDINATION.md) now feeds the same device/circuit data into calculations, DXF and IFC. A geometry companion only adds explicit dimensions, heights and spaces. Reopened artifacts are reconciled; the workflow can send the resulting DXF through native AutoCAD save/reopen/plot. No separate power, PF, XY or circuit copy is maintained in geometry inputs.

## Real photometric engine

[Lighting analysis](docs/LIGHTING.md) runs official Radiance against sourced IES files, computes direct/reflected sensor illuminance and checks a higher-quality verification run. A synthetic fixture has been checked against the inverse-square/cosine law and maintenance scaling. Arbitrary geometry, glare/daylight and full lighting acceptance remain pending.
