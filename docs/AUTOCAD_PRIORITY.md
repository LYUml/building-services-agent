# Current priority: AutoCAD and real assignment delivery

The user explicitly prioritizes AutoCAD and real coursework end-to-end results.
Pause new Revit adaptation/debugging. Preserve the complete general building-
services goal, replaceable Hong Kong rules and all source/quality constraints.
Existing running validation/evidence should finish without restarting user apps,
closing unsaved documents or retroactively changing old hashes.

## Upstream comparison candidates

The original review was source-only. Actual follow-up: the dcc framework import is
blocked by host Application Control; the U-C4N independent DXF backend now reads
the same real native-exported source successfully. Full MCP/COM/write/plot
integration is not established. See AUTOCAD_SOURCE_PROVIDER.md.
They were cloned under ignored tools and their clean commit/license/source hashes
are recorded in evidence/autocad-reuse-review.json.

| Candidate | Fixed commit | Observed source and next gate |
|---|---|---|
| [dcc-mcp-autocad](https://github.com/dcc-mcp/dcc-mcp-autocad/tree/d2acd4859b5a724b6032bd3044684291972a26e2) | d2acd4859b5a724b6032bd3044684291972a26e2; MIT | Separate COM/Core Console transports and forced transport option. Core Console actually pipes a script to stdin and reads the saved DWG back. Its inspection currently returns layouts=[Model], so it cannot alone prove actual paperspace/layout coverage. Pin dcc-mcp-core before execution and test against installed AutoCAD2027. |
| [U-C4N/Autocad-MCP](https://github.com/U-C4N/Autocad-MCP/tree/6f6a538255ca9f885232e845ac32f10b4433fe3e) | 6f6a538255ca9f885232e845ac32f10b4433fe3e; MIT | Live COM/headless DXF architecture and declared document binding/edit guards. Published ranges include FastMCP3.x; isolate and pin dependencies instead of upgrading this agent environment. Guard behavior and side effects need local verification. |

Repository tool counts, production-grade labels and recorded upstream smoke claims
are not this host's executed evidence. Do not automatically fall back to live COM
when evaluating a headless path. Every live write still needs the actual document
path checked; do not close user documents or restart applications.

First compare dcc's closest Core Console path with existing native_cad/cad_intake,
then consider the second candidate for demonstrated gaps. Reuse proven transport,
block/layer/dimension/plot features through thin adapters; preserve existing
working parts. Do not replace source interpretation, engineering inputs/targets,
Hong Kong applicability, orchestration or final review with generic drawing tools.

## Same-task acceptance

Use an explicitly selected real project: original brief and source DWG copies,
confirmed design inputs, one required building-services change, editable DWG,
actual scale plot/PDF, calculation/equipment schedule and report. Compare source
units, document identity, entity/layer/block/annotation/layout coverage, saved
reopen and every required plot page. Preserve missing dimensions/product/code
applicability and normal engineering gaps. A new bridge is adopted only after
that native/source/visual evidence, not after import or a listing of tools.

BSE3227 inputs/runs/deliverables stay in Desktop/polyu_bse3227 under explicit host
BSA_PROJECT_ROOT. Public fixtures/tools/tests stay here; historical runs remain.
Check staged files, exclusions and remote HEAD separately before publishing each
repository. No private source archives, student lists, credentials, environments
or runtime records belong in public snapshots.

The current compact-elbow IFC milestone is a completed supporting optimization,
not the replacement main objective. Tool/test counts are not the product progress
measure; the next main check is real AutoCAD assignment output at a defined gate.
