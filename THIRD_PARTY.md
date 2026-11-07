# Attribution and upstream integration register

Research checked 2026-11-08. These are integration candidates, not bundled implementations. A link is not a license audit, compatibility test or evidence of an executed integration. Before vendoring or installing, record exact commit/version, inspect its license and preserve required notices. Papers are methodology references, not proof of a runnable tool.

| Upstream | Intended use | Initial license observation / status |
|---|---|---|
| https://github.com/U-C4N/Autocad-MCP | live AutoCAD COM authoring and inspection; study workflow skill | repository advertises MIT; not installed here |
| https://github.com/NatLabRockies/openstudio-mcp | OpenStudio/EnergyPlus model creation, simulation, workflow skills | inspect LICENSE.txt at pinned revision before reuse; not installed |
| https://github.com/LBNL-ETA/EnergyPlus-MCP | alternative IDF inspection/simulation | inspect License.txt at pinned revision; not installed |
| https://github.com/Show2Instruct/bonsai-mcp | IFC semantic authoring through Bonsai/IfcOpenShell | inspect license at pinned revision; not installed |
| https://github.com/ladybug-tools/honeybee-radiance | lighting and daylight analysis | AGPL family; inspect selected component/revision before integration |

The Python engine, DXF integration wrapper and skills are original code authored for this project; DXF serialization uses ezdxf as credited below. The completed BSE3124 workflow informed provenance, common device/circuit data, native CAD verification, and visual acceptance practices; no coursework assets are redistributed.

## Installed runtime dependency

- **ezdxf 1.4.5**, MIT, https://github.com/mozman/ezdxf — used as an installed library for DXF document writing and independent reload checks; not vendored. Its distribution retains upstream license notices. The initial handwritten R12 writer was replaced after inspection showed missing explicit metre units/layer table declarations. No DWG fidelity claim is inferred.
- **PyYAML 6.0.3**, MIT, https://github.com/yaml/pyyaml — development-only prerequisite for the host skill validator, not used by runtime calculations.

## Executed energy integrations

- **OpenStudio(R) SDK 3.11.0** installed as an optional Python library. Original two-zone authoring code calls the official SDK and its ForwardTranslator. It targets EnergyPlus 25.2.0; matching was checked at runtime. This project is not an endorsed or renamed version of OpenStudio.
- **EnergyPlus 25.2.0-cf7368216c**, official Windows x64 portable release, SHA256 `4136901f7e1708f6536d84278e26ad88b414c7efc905febf6d49c2539a36f3cd` (archive, verified against GitHub asset digest). Actual engine executes translated IDFs with ExpandObjects; binary package stays ignored under tools. License retained at third_party/licenses/energyplus.txt.
- **openstudio-mcp**, commit `9f8b6bd0b5a58fd4f97cfd8b9f7393f222a1bb43`, installed from its unmodified checkout; its OpenStudio license is retained at third_party/licenses/openstudio-mcp.txt. Stdio MCP initialization, tool discovery, model loading, space and zone queries were executed against our generated model. Simulation in this milestone uses our SDK/engine adapter, not the upstream simulation tool.
- Observed upstream limitation: get_building_info returns structured `ok:false` for this unoccupied model (division by zero in floorAreaPerPerson). We do not insert artificial people to hide it; the probe uses space/zone queries and treats structured failures as failures. Windows native execution does not provide the upstream Linux sandbox; generated-code tools are disabled for this read-only probe.
