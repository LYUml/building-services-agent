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

## Document and OCR integrations

- **pypdf 7.0.0**, BSD-3-Clause, https://github.com/py-pdf/pypdf — optional read-only PDF text/page extraction. Installed distribution license retained at third_party/licenses/pypdf.txt.
- **rapidocr_onnxruntime 1.4.4**, Apache-2.0, https://github.com/RapidAI/RapidOCR — optional offline OCR wrapper with bundled PP-OCRv4 detection/recognition and mobile classification models originating from PaddleOCR (https://github.com/PaddlePaddle/PaddleOCR). No upstream source or model binaries are vendored. Installed package metadata declares Apache-2.0; upstream main-branch license retrieved 2026-11-08 is retained at third_party/licenses/rapidocr.txt, with its hash in docs/evidence/document-intake/review.json. This is not an audited license inventory of every transitive binary component. Model hashes and actual inference versions are recorded per run.
- **ONNX Runtime 1.31.1**, MIT, https://github.com/microsoft/onnxruntime; **opencv-python 5.0.0.93**, upstream OpenCV licensing, https://github.com/opencv/opencv-python — pinned OCR optional dependencies; remain installed packages rather than copied source.
- **Poppler pdftoppm**, https://poppler.freedesktop.org/ — external local PDF renderer, not redistributed here; record executable checksum in OCR evidence and supply your own compatible binary.

RapidOCR legacy package was selected for bundled local models, avoiding implicit runtime downloads and making model checksums available. It is not asserted to be the latest RapidOCR API or a general engineering-document understanding model.
