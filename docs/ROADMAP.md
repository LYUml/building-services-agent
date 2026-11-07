# Scope and acceptance

The requested end state is reusable automation from a requirement document and source drawings to editable models, plotted drawings, performance analysis and a source-backed report. Multiple assignments must reuse the same tools without inheriting course-specific numbers.

| Workstream | Acceptance evidence | Current state |
|---|---|---|
| Requirements intake | brief page/section to deliverable and verification mapping; unresolved data visible | skill procedure; automatic parsing pending |
| Shared project data | validated identities, units, references and input provenance | electrical JSON implemented |
| Electrical | counts reconcile, independent formula examples, cable/protection and fault checks | basic conditional checks; fault checks pending |
| Native CAD | preserve supplied base, units/sample proof, native DWG reopen and inspected PDF | DXF overlay only |
| BIM | semantically valid systems/components and schedules, editable IFC/RVT | integration pending |
| HVAC/energy | actual engine execution, geometry/inputs QA, heat/electric outputs separate | OpenStudio-MCP candidate; not executed |
| Lighting | photometry and calculation grid with target checks | Radiance/Honeybee candidate; not executed |
| Plumbing/fire | hydraulic calculations and domain-specific applicable rules | pending |
| Delivery | input hashes unchanged, output counts match, visual checks with evidence | hashes and device count check implemented; visual gate pending |
| Reuse | second independent brief run, evidence of adaptation without copied assumptions | pending |

## Next sequence

1. Exercise the electrical slice against malformed inputs and independent hand calculations.
2. Connect live AutoCAD with scoped writes; create a new synthetic native drawing, reopen and inspect plotted output. Never use the finished coursework as the development sandbox.
3. Integrate an attributed, pinned OpenStudio-MCP deployment and run a real two-zone energy workflow.
4. Add document intake and requirement tracking, existing-drawing spatial extraction and checked authoring plans.
5. Add lighting, HVAC network and hydraulic modules, BIM system semantics and cross-artifact gates.
6. Run two independent requirement documents end to end and audit every promised deliverable.

Do not mark the overall objective complete at a foundation milestone.
