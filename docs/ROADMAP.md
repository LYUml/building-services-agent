# Scope and acceptance

The requested end state is reusable automation from a requirement document and source drawings to editable models, plotted drawings, performance analysis and a source-backed report. Multiple assignments must reuse the same tools without inheriting course-specific numbers.

| Workstream | Acceptance evidence | Current state |
|---|---|---|
| Requirements intake | brief page/section to deliverable and verification mapping; unresolved data visible | text passage indexing, source-linked host-AI plan validation and tool orchestration implemented; PDF/Word locators and offline OCR/review gates implemented; general semantic coverage and drawing interpretation pending |
| Shared project data | validated identities, units, references and input provenance | electrical JSON implemented |
| Electrical | counts reconcile, independent formula examples, cable/protection and fault checks | basic conditional checks; fault checks pending |
| Native CAD | preserve supplied base, units/sample proof, native DWG reopen and inspected PDF | synthetic overlay native save/reopen/plot verified; existing base and fixed-scale sheets pending |
| BIM | semantically valid systems/components and schedules, editable IFC/RVT | IFC4 envelope geometry, spaces, systems and directed port topology generated/reopened/checked; detailed models, schedules and RVT pending |
| HVAC/energy | actual engine execution, geometry/inputs QA, heat/electric outputs separate | OpenStudio/EnergyPlus synthetic two-zone design-day comparison executed; MCP read queries verified; circular level-air tree pressure budgets implemented; annual/weather and broad HVAC authoring pending |
| Lighting | photometry and calculation grid with target checks | Radiance/Honeybee candidate; not executed |
| Plumbing/fire | hydraulic calculations and domain-specific applicable rules | circular prescribed-demand water tree pressure budgets implemented; loops, drainage, fire demand methods and domain rules pending |
| Delivery | input hashes unchanged, output counts match, visual checks with evidence | workflow input/output integrity, source locators and task evidence matrix implemented; full acceptance gates pending |
| Reuse | second independent brief run, evidence of adaptation without copied assumptions | pending |

## Next sequence

1. Exercise the electrical slice against malformed inputs and independent hand calculations.
2. Connect live AutoCAD with scoped writes; create a new synthetic native drawing, reopen and inspect plotted output. Never use the finished coursework as the development sandbox.
3. Integrate an attributed, pinned OpenStudio-MCP deployment and run a real two-zone energy workflow.
4. Add document intake and requirement tracking, existing-drawing spatial extraction and checked authoring plans.
5. Add lighting, HVAC network and hydraulic modules, BIM system semantics and cross-artifact gates.
6. Run two independent requirement documents end to end and audit every promised deliverable.

Do not mark the overall objective complete at a foundation milestone.
