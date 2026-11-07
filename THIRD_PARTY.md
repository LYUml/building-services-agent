# Attribution and upstream integration register

Research checked 2026-11-08. These are integration candidates, not bundled implementations. A link is not a license audit, compatibility test or evidence of an executed integration. Before vendoring or installing, record exact commit/version, inspect its license and preserve required notices. Papers are methodology references, not proof of a runnable tool.

| Upstream | Intended use | Initial license observation / status |
|---|---|---|
| https://github.com/U-C4N/Autocad-MCP | live AutoCAD COM authoring and inspection; study workflow skill | repository advertises MIT; not installed here |
| https://github.com/NatLabRockies/openstudio-mcp | OpenStudio/EnergyPlus model creation, simulation, workflow skills | inspect LICENSE.txt at pinned revision before reuse; not installed |
| https://github.com/LBNL-ETA/EnergyPlus-MCP | alternative IDF inspection/simulation | inspect License.txt at pinned revision; not installed |
| https://github.com/Show2Instruct/bonsai-mcp | IFC semantic authoring through Bonsai/IfcOpenShell | inspect license at pinned revision; not installed |
| https://github.com/ladybug-tools/honeybee-radiance | lighting and daylight analysis | AGPL family; inspect selected component/revision before integration |

The initial Python engine, DXF writer and skills are original code authored for this project. The completed BSE3124 workflow informed provenance, common device/circuit data, native CAD verification, and visual acceptance practices; no coursework assets are redistributed.
