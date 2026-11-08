# Attribution and upstream integration register

## Executed EPANET water graphs

**WNTR 1.5.0**, revised BSD, [USEPA source tag](https://github.com/USEPA/WNTR/tree/1.5.0), is a pinned optional `water` dependency. Original orchestration calls its EpanetSimulator with EPANET 2.2 and retains native inputs/results; no upstream source or binaries are vendored. The installed distribution's exact license text is preserved at `third_party/licenses/wntr-1.5.0.txt`, including its EPANET MIT and NumPy notices. The EPANET 2.2 [AUTHORS](https://github.com/OpenWaterAnalytics/EPANET/blob/v2.2/AUTHORS) notice is preserved at `third_party/licenses/epanet-2.2-authors.txt`. These reference notices do not establish an exact source commit for the wheel's bundled native library. Actual engine version/DLL SHA256 and WNTR/NumPy/SciPy/pandas versions are recorded in each run. Dependencies remain installed packages; a full transitive lock/license audit is not claimed.

Research checked 2026-11-08. These are integration candidates, not bundled implementations. A link is not a license audit, compatibility test or evidence of an executed integration. Before vendoring or installing, record exact commit/version, inspect its license and preserve required notices. Papers are methodology references, not proof of a runnable tool.

| Upstream | Intended use | Initial license observation / status |
|---|---|---|
| https://github.com/U-C4N/Autocad-MCP | live AutoCAD COM authoring and inspection; study workflow skill | repository advertises MIT; not installed here |
| https://github.com/NatLabRockies/openstudio-mcp | OpenStudio/EnergyPlus model creation, simulation, workflow skills | inspect LICENSE.txt at pinned revision before reuse; not installed |
| https://github.com/LBNL-ETA/EnergyPlus-MCP | alternative IDF inspection/simulation | inspect License.txt at pinned revision; not installed |
| https://github.com/Show2Instruct/bonsai-mcp | IFC semantic authoring through Bonsai/IfcOpenShell | inspect license at pinned revision; not installed |
| https://github.com/ladybug-tools/honeybee-radiance | lighting and daylight analysis | AGPL family; inspect selected component/revision before integration |

The Python engine, DXF integration wrapper and skills are original code authored for this project; DXF serialization uses ezdxf as credited below. The completed BSE3124 workflow informed provenance, common device/circuit data, native CAD verification, and visual acceptance practices; no coursework assets are redistributed.

Saved-IFC segment schedule/projection code is original integration using the already pinned IfcOpenShell 0.8.5 placement/system/unit APIs and ezdxf 1.4.5. No additional dependency or upstream source is bundled. The optional recorded preview was rendered by a local isolated headless Microsoft Edge process; Edge is not redistributed and SVG inspection does not establish native CAD acceptance.

Native IFC-diagram delivery reuses the original isolated AutoCAD export and ezdxf reconciliation adapters, with additional complete model/XDATA identity checks and the existing pypdf physical-reference verifier. AutoCAD 2027 is the user's licensed local engine, not redistributed. Actual PDF previews use the already credited Poppler runtime; no new dependency or third-party source is vendored.

The fixed-speed single-line pump intersection/bisection and power accounting are original orchestration around the pinned fluids 1.3.1 pressure engine. No new dependency or upstream source is copied. Method references are the [Hydraulic Institute combined pump/system curves](https://datatool.pumps.org/pump-fundamentals/combined.html), [pump curve definitions](https://datatool.pumps.org/pump-fundamentals/pump-curves) and [US DOE pumping sourcebook](https://www.energy.gov/sites/prod/files/2014/05/f16/pump.pdf). Combined wire-to-water efficiency is an explicit input assumption, distinct from pump-only shaft efficiency. References do not certify synthetic curve points or manufacturer suitability.

Pump/electrical/IFC property binding is original integration using the same pinned fluids, IfcOpenShell and ezdxf libraries. No upstream source or new dependency is vendored. [DOE motor load/efficiency guidance](https://www.energy.gov/sites/prod/files/2014/04/f15/10097517.pdf) supports keeping operating estimates, load-dependent PF and rated motor data distinct; it supplies no embedded motor defaults or regulation tables.

Source-bound delivery review code is original and uses the Python standard library plus existing workflow/hash helpers. No new dependency or upstream source is copied. The retained SVG evidence image was produced by an isolated local headless Microsoft Edge renderer, not bundled with the project. Review hashes do not authenticate reviewers or certify engineering completeness.

Conditional TN fault-envelope verification is original Python standard-library code; no upstream implementation or regulation table is copied. Method references are Schneider Electric's [TN protection](https://www.electrical-installation.org/enwiki/TN_system_-_Principle), [breaker capacity](https://www.electrical-installation.org/enwiki/Other_characteristics_of_a_circuit-breaker), [thermal withstand](https://www.electrical-installation.org/enwiki/Verification_of_the_withstand_capabilities_of_cables_under_short-circuit_conditions), and Siemens' [MCB primer](https://cache.industry.siemens.com/dl/files/304/109482304/att_866617/v1/MiniatureCircuitBreakers_primer_EN_201601250852395217.pdf). All numerical guarantees/limits in the fixture are synthetic inputs, not imported manufacturer data or a local compliance decision.

## Installed runtime dependency

- **ezdxf 1.4.5**, MIT, https://github.com/mozman/ezdxf — used as an installed library for DXF document writing and independent reload checks; not vendored. Its distribution retains upstream license notices. The initial handwritten R12 writer was replaced after inspection showed missing explicit metre units/layer table declarations. No DWG fidelity claim is inferred.
- **PyYAML 6.0.3**, MIT, https://github.com/yaml/pyyaml — development-only prerequisite for the host skill validator, not used by runtime calculations.

Drawing intake also uses the pinned ezdxf library for read-only entity inventory and OCS-to-WCS coordinates. Original selection/hash/unit-proof and straight-polygon area code is provided in bsa.cad_intake. Native DWG export requires the user's licensed AutoCAD installation and runs on isolated copies; AutoCAD is not redistributed.

Base-overlay preservation and physical PDF-scale verification are original adapters using the same pinned ezdxf/pypdf packages. The PDF verifier interprets stroked paths and transformation matrices; no upstream implementation is copied. AutoCAD handles native save/reopen/export and plotting locally; generated PDFs are independently rendered with the already credited Poppler installation.

Finite-catalogue network design search is original orchestration around the existing fluids-backed pressure solver. It enumerates supplied options and retains conditional comparison evidence; no new solver source is copied. Existing fluids attribution and pinned runtime apply. Independent laminar and velocity-bound tests are method checks, not upstream product or code certification.

Model-aware sizing/revision uses the existing pinned IfcOpenShell/fluids libraries plus original fixed-centreline envelope and reconciliation code. Stable IFC object/port identities use Python's standard UUID namespace mechanism and IfcOpenShell's GUID compression API; no new dependency or upstream source is vendored. The stability contract covers declared objects/ports, not every IFC relationship or file bytes.

Straight circular wall authoring uses the same pinned IfcOpenShell 0.8.5 runtime and the normative IFC4 [IfcCircleHollowProfileDef](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcprofileresource/lexical/ifccirclehollowprofiledef.htm) schema contract. Original QA code checks the native profile, topology, signed mesh volume and port axes. Mesher settings were verified against the installed runtime and referenced in [official documentation](https://docs.ifcopenshell.org/ifcopenshell/geometry_settings); no newer runtime or copied source is bundled. Standard mathematical annular-volume and manifold checks do not certify materials, fabrication or professional compliance.

## Geometry coordination integration

- **Manifold3D 3.5.4**, Apache-2.0, [source tag](https://github.com/elalish/manifold/tree/v3.5.4), [package release](https://pypi.org/project/manifold3d/3.5.4/) — installed as a pinned optional `clash` dependency, not vendored. Its double-precision Mesh64 Boolean intersections supplement a demonstrated aligned/coplanar overlap blind spot in the installed IfcOpenShell 0.8.5 triangle intersection queries. Arbitrary accepted closed meshes, including rotated tessellated bodies and hollow walls, use the same backend; bounding boxes only screen candidates.
- The installed distribution's unmodified LICENSE and AUTHORS are retained at third_party/licenses/manifold3d.txt and manifold3d-authors.txt, with exact byte preservation in .gitattributes. Their SHA256 values are recorded in docs/evidence/ifc-clash/runtime.json alongside the installed module hash/runtime versions. This is package provenance and top-level attribution, not a full transitive native-binary license audit.
- Original policy/contact/coverage/orchestration code uses the existing pinned IfcOpenShell geometry iterator and clearance interface, plus Manifold3D. No upstream source is copied or renamed. Product geometry accuracy, threshold applicability and professional acceptance remain independent gates.

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
