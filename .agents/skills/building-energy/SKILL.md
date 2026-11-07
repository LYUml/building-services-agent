---
name: building-energy
description: Build, simulate and analyze building thermal and HVAC energy models using OpenStudio/EnergyPlus, with source-backed inputs and explicit model QA.
---

# building-energy

Prefer an inspected and pinned OpenStudio-MCP deployment for creating OSM geometry and systems; consider LBNL EnergyPlus-MCP for existing IDF workflows. See THIRD_PARTY.md. These integrations are candidates until a real engine run is evidenced. Never report an invented or surrogate simulation as an EnergyPlus result.
Prepare thermal spaces, adjacent surface conditions, constructions, weather/design days, internal gains, schedules, ventilation, infiltration, setpoints and systems. Record assumptions and match geometry to the source. An ideal-load model assesses loads, not a fully specified plant's electricity.
Use upstream capability discovery and bundled workflow skills, not guessed tool names. Save OSM/IDF, engine version, weather hash, run command/tool calls, error logs, SQLite/CSV results and report. Resolve severe/fatal errors; evaluate warnings and unmet hours. Compare a baseline and one controlled variant with identical conditions.
Keep cooling/heating kW, electrical kW, annual kWh and COP distinct. Simulation system topology does not prove spatially routed BIM ductwork/piping. Read output units and sizing conditions before interpreting peaks. Never silently apply ASHRAE baseline templates as Hong Kong course requirements.

## Repository engine adapter
For the supported synthetic two-adjacent-zone design-day comparison, use `python -m bsa.energy <project.json> --out <new-run> --energyplus <engine.exe>`. Schema example: examples/two-zone-energy/project.json. Restore the pinned Windows x64 tools with scripts/setup_energy.py; see README.md and THIRD_PARTY.md. Inspect analysis.json, OSM/IDF and eplusout.err. This adapter is not a general arbitrary-building or annual-weather pipeline.
The read-only upstream probe is `python scripts/probe_openstudio_mcp.py <generated-model.osm>`. It tests MCP model load and space/zone queries; no upstream simulation execution is claimed. A tool may return isError=false but structured ok=false; treat either failure as failure.
