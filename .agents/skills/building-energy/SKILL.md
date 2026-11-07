---
name: building-energy
description: Build, simulate and analyze building thermal and HVAC energy models using OpenStudio/EnergyPlus, with source-backed inputs and explicit model QA.
---

# building-energy

Prefer an inspected and pinned OpenStudio-MCP deployment for creating OSM geometry and systems; consider LBNL EnergyPlus-MCP for existing IDF workflows. See THIRD_PARTY.md. These integrations are candidates until a real engine run is evidenced. Never report an invented or surrogate simulation as an EnergyPlus result.
Prepare thermal spaces, adjacent surface conditions, constructions, weather/design days, internal gains, schedules, ventilation, infiltration, setpoints and systems. Record assumptions and match geometry to the source. An ideal-load model assesses loads, not a fully specified plant's electricity.
Use upstream capability discovery and bundled workflow skills, not guessed tool names. Save OSM/IDF, engine version, weather hash, run command/tool calls, error logs, SQLite/CSV results and report. Resolve severe/fatal errors; evaluate warnings and unmet hours. Compare a baseline and one controlled variant with identical conditions.
Keep cooling/heating kW, electrical kW, annual kWh and COP distinct. Simulation system topology does not prove spatially routed BIM ductwork/piping. Read output units and sizing conditions before interpreting peaks. Never silently apply ASHRAE baseline templates as Hong Kong course requirements.
