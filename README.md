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

Native DWG production, existing-bottom-drawing integration, BIM authoring, energy simulation and other MEP domains remain work in progress. See [roadmap](docs/ROADMAP.md), [project format](docs/PROJECT_FORMAT.md), and [upstream attribution](THIRD_PARTY.md). No upstream implementation has been copied into this initial milestone.
