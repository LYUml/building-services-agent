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

Drawing intake also uses the pinned ezdxf library for read-only entity inventory and OCS-to-WCS coordinates. Original selection/hash/unit-proof and straight-polygon area code is provided in bsa.cad_intake. Native DWG export requires the user's licensed AutoCAD installation and runs on isolated copies; AutoCAD is not redistributed.

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

## Executed IFC integration

- **IfcOpenShell 0.8.5**, LGPL-3.0-or-later as declared by installed wheel metadata, https://github.com/IfcOpenShell/IfcOpenShell — used as an optional installed library for IFC4 authoring, geometry evaluation and schema/EXPRESS checking. No source or native binary is vendored. Original project code calls documented APIs (https://docs.ifcopenshell.org/). The repository does not expose a v0.8.5 source tag; no claim is made to have audited a matching source revision. Upstream v0.9.0 COPYING and COPYING.LESSER texts are retained as license reference copies, not represented as exact wheel-source provenance.
- **pytest 9.2.0**, MIT, https://github.com/pytest-dev/pytest — required by the selected IfcOpenShell EXPRESS rule executor; it is part of the optional BIM dependencies even when unittest runs the project's tests.

Observed upstream runtime diagnostic: EXPRESS rule loading emits a Python ResourceWarning for an unclosed rules source file. The generated IFC schema/EXPRESS diagnostics themselves were empty for both fixtures. Upstream code was not modified to suppress the warning.

## Network calculation library

- **fluids 1.3.1**, MIT, Caleb Bell and contributors, https://github.com/CalebBell/fluids — installed optional library used for the turbulent Colebrook Darcy factor. License from the selected wheel retained at third_party/licenses/fluids.txt. Method documentation: https://fluids.readthedocs.io/fluids.friction.html. The original project code implements prescribed-demand tree aggregation, source/elevation budgets and reporting; no upstream network solver is implied.
- Installed SciPy version for this milestone: 1.18.1 (transitive dependency). Neither library implementation nor binary dependencies are vendored. A full multi-platform transitive lock is not claimed.

## Executed Radiance integration

- **Radiance 6.0.2**, official release rad6R0P2 / binary c1700d56cc, https://github.com/LBNL-ETA/Radiance — original adapter calls ies2rad, xform, oconv and rtrace. Windows archive SHA256 `c4f02efcb4a33f4a43b7ce0ba58100544abc317a1be61f7b0425a64a66eb8a09` matched the GitHub release asset digest. Bootstrap checks installed bytes against that archive. No binary or engine source is vendored.
- Radiance Software License v2.0 from the selected c1700d56 upstream revision is retained at third_party/licenses/radiance.txt. Its upstream header is retained unchanged. This project is not endorsed by the Radiance authors or LBNL.
- All IES files currently committed under examples/lighting are original synthetic verification distributions, not manufacturer data. No electrical watt-to-photometry conversion or general photometry certification is claimed.
