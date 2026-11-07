# Scope and acceptance

The requested end state is reusable automation from a requirement document and source drawings to editable models, plotted drawings, performance analysis and a source-backed report. Multiple assignments must reuse the same tools without inheriting course-specific numbers.

| Workstream | Acceptance evidence | Current state |
|---|---|---|
| Requirements intake | brief page/section to deliverable and verification mapping; unresolved data visible | source-linked document plans, PDF/Word/OCR review gates and read-only DWG/DXF inventory with hash-bound unit-checked straight polygon measurements implemented; general semantic interpretation pending |
| Shared project data | validated identities, units, references and input provenance | shared electrical/CAD/IFC/optical data, port-derived network geometry and explicit pump operating/electrical/IFC-property binding implemented; baseline loads/hardware retained; universal binding and electrical topology pending |
| Electrical | counts reconcile, independent formula examples, cable/protection and fault checks | basic conditional checks; fault checks pending |
| Native CAD | preserve supplied base, units/sample proof, native DWG reopen and inspected PDF | supported base/device overlays and IFC-derived centreline diagrams saved/reopened; diagram model GUIDs retained; synthetic fixed-scale A4 PDF references and actual visual reviews verified; arbitrary fidelity, full sheet standards and broad source adaptation pending |
| BIM | semantically valid systems/components and schedules, editable IFC/RVT | IFC4 envelopes and explicit straight circular walls, spaces, systems and ports generated/reopened/checked; saved hollow segment schedules and projected DXF implemented; full schedules, detailed fittings/products and RVT pending |
| HVAC/energy | actual engine execution, geometry/inputs QA, heat/electric outputs separate | OpenStudio/EnergyPlus synthetic two-zone design-day comparison executed; MCP read queries verified; circular level-air tree pressure budgets implemented; annual/weather and broad HVAC authoring pending |
| Lighting | photometry and calculation grid with target checks | actual Radiance IES direct/reflected points and numerical stability verified; shared electrical/CAD/IFC origins bound to Radiance; arbitrary scenes, glare/daylight and final acceptance pending |
| Plumbing/fire | hydraulic calculations and domain-specific applicable rules | circular prescribed-demand water trees and sourced single-terminal fixed-speed pump/system intersections implemented; branches with pressure-dependent flow, loops, drainage, fire demand methods and domain rules pending |
| Design iteration | retained baseline/failed candidates, explicit objective/constraints and selected rerun | finite-catalogue circular sizing and fixed-endpoint IFC envelope revision with stable object/port IDs implemented; cross-domain iteration, detailed geometry and full acceptance pending |
| Geometry coordination | saved geometry intersections, clearances, scope/exception and coverage evidence | IFC triangle queries plus Manifold3D Mesh64 overlap checks; optional conservative bidirectional outside-joint clearance proofs implemented; product/visual acceptance pending |
| Delivery | input hashes unchanged, output counts match, visual checks with evidence | workflow input/output integrity, source locators and task evidence matrix implemented; full acceptance gates pending |
| Reuse | second independent brief run, evidence of adaptation without copied assumptions | independent synthetic vertical water-riser/electrical brief executed through unchanged adapters; gravity, four-size selection, saved hollow IFC, clearance and electrical DXF checked; full multi-project deliverable/visual acceptance pending |

## Next sequence

1. Exercise the electrical slice against malformed inputs and independent hand calculations.
2. Connect live AutoCAD with scoped writes; create a new synthetic native drawing, reopen and inspect plotted output. Never use the finished coursework as the development sandbox.
3. Integrate an attributed, pinned OpenStudio-MCP deployment and run a real two-zone energy workflow.
4. Add document intake and requirement tracking, existing-drawing spatial extraction and checked authoring plans.
5. Add lighting, HVAC network and hydraulic modules, BIM system semantics and cross-artifact gates.
6. Run two independent requirement documents end to end and audit every promised deliverable.

Do not mark the overall objective complete at a foundation milestone.
