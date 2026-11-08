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

For complete hourly weather years, read docs/ANNUAL_ENERGY.md and use `annual_energy`/`bsa.annual_energy`. Require declared EPW source/station/raw hash, exact calendar coverage, real site derivation, explicit budgets and per-zone unmet-time targets. Preserve hourly/monthly/annual reconciliation and independent lighting balance. Keep supplied thermal loads distinct from lighting electricity and plant input; no invented COP/EUI or net HVAC saving. Inspect completion.json under docs/ENERGY_COMPLETION.md: only the exact inspected executable/source-order limitation can explain initialized false SQL flags, and all other completion facts must pass. Never rewrite native flags or clear failures/unknown exceptions. The example is Chicago TMY3 with synthetic geometry. Actual construction/gains/schedules/weather/HVAC/plant/calibration and domain acceptance remain pending.

For explicit multi-space annual models use examples/annual-energy/three-spaces.json. Require per-space geometry sources and metre-valued boxes. Reject overlap/partial-face contact; inspect reciprocal matching identities/areas and exact hourly zone/light key coverage. Full-face stacked adjacency is supported; arbitrary footprints, partial-face subdivision remain pending; saved box-space binding is supported under docs/THERMAL_BINDING.md.

For saved IFC thermal geometry use `annual_energy_ifc` in examples/thermal-ifc-plan.json or bsa.thermal_binding. Require complete GUID-to-zone mapping, per-space sources and explicit EnergyPlus north-axis angle. The project template must omit geometry/orientation. Read actual saved solid world coordinates; check box corners, boundary triangles, closed winding, face areas and volume, not bounds alone. IFC TrueNorth/georeferencing, constructions, boundaries, schedules and system objects are not automatically imported. Preserve source IFC and bind model/result identities with hashes; generic box space does not establish a real thermal boundary.
