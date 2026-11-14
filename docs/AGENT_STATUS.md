# Whole-agent status


## Current verification checkpoint — 2026-11-14

This is a reusable multi-discipline agent under development, not a completed
arbitrary-brief-to-accepted-design system. The capability/gap matrix below remains
the whole-agent scope; a coursework replay does not replace it.

All 385 selected modules have completed in 20 batches: 1,617 executed instances,
1,477 passes, 126 skips, one failure and 13 errors. All terminal receipts
independently verify against current selected source bytes. All 13 error traces
record OpenStudio's `_openstudioutilitiesunits` blocked by Application Control.
The failure is a dependent HVAC rule assertion whose upstream energy task did not
pass. The full run completed but did not pass. Counts include imported repeated
test instances and are not an agent completion percentage. See the
[complete aggregate](evidence/agent-regression-complete.json) and
[triage and remaining work](REGRESSION_20261114.md).

Separate opt-in runs reverify five actual AutoCAD integration cases and nine
source-gated Hong Kong cable controls. A separate 24-case pinned MOOSAS geometry
and source/rule workflow replay also passes without skips; this does not run its
airflow or thermal engines. See [MOOSAS evidence](evidence/moosas-geometry-regression.json).
Their scopes and remaining visual/design
gates are preserved in [native route evidence](evidence/native-riser-route-regression.json),
[initial native checkpoint](evidence/agent-regression-checkpoint.json) and
[Hong Kong source evidence](evidence/hk-cable-regression-source-check.json).
A separate [three-view native test](evidence/native-multiview-regression.json)
passes actual save/reopen, merged-page and 100 mm reference checks, with visual
review pending.
Separate three-phase opt-ins now execute 36 numerical/source/IFC workflow
controls with no skips, using pinned pandapower and the existing isolated host.
Both receipts verify. See [electrical evidence](evidence/three-phase-regression-opt-in.json).
Product, protection and complete project/code acceptance remain open.
A further 18 numerical/HK current-balance/IFC workflow controls pass with the
exact pinned BEC cache, including fail/pending and source-substitution controls.
See [Hong Kong electrical evidence](evidence/three-phase-hk-regression.json).
Revit native creation/save/reopen remains unverified; opening a test copy alone
is not that acceptance. See [actual Revit observation](REVIT_BUILTIN_INTERCHANGE.md).

Explicit local runtime refresh now preserves user controls and unspecified
programs, with pinned TOML Kit, backups and atomic replacement. Seven tests and
actual Codex backend reads pass; both live workspace configs remain unchanged.
See docs/CODEX_LOCAL_SETUP.md.

Project-scoped local Codex startup now separates development and coursework
data roots. Both actual Codex backends discover 38 BSA tools and execute reads;
the active development chat also calls BSA and rejects an outside-root read.
Three installer tests pass; full engineering acceptance remains open.
See docs/CODEX_LOCAL_SETUP.md.

The pressure ledger now directly reconstructs cached paths using the existing
port-topology router. Thirteen tests and complete real-client replay pass;
all 20 outlet/45 gap reads match. Physical joints and full pressure remain open.
See docs/SOURCE_PRESSURE_LEDGER.md.

Ledger checks now reject tiny wrong subtotals, duplicate/unused straight
definitions and boolean counts. Twelve tests and fresh complete MCP replay pass;
the real 20-outlet ledger payload is unchanged. Engineering remains incomplete.
See docs/SOURCE_PRESSURE_LEDGER.md.

AI clients now generate/independently inspect pressure evidence ledgers and
read exact signed/null outlet records. Actual 45-gap pagination and all 20
outlet reads match saved evidence; seven tests pass. Full fan duty remains open.
See docs/MCP_PRESSURE_LEDGER.md.

Reference arithmetic now rejects reproduced tiny-value false matches and
nonzero underflow instead of silently accepting zero. Nine tests pass; fresh
real-source audit retains all four differences and adds no formal loss values.
See docs/LOSS_REFERENCE.md.

Signed coefficient reference review now verifies common-port pressure
invariance and source/native arithmetic. Four candidate differences remain
after normalization; seven tests and saved replay pass. No method is adopted.
See docs/LOSS_REFERENCE.md.

Pinned upstream contraction data now supports a bounded data-only crosscheck:
4 of 31 native transitions are numerically bounded; 27 retain explicit angle/
range rejection. No upstream package integration or new formal loss is claimed.
See docs/CONTRACTION_CANDIDATE.md.

Independent pressure evidence now reconciles all 20 outlet paths and maps 45
numerical fitting gaps to affected outlets. Source/saved-ledger replay and two
tests pass. No new loss data or complete fan duty is inferred.
See docs/SOURCE_PRESSURE_LEDGER.md.

AI-client MCP now executes tagged native delivery, independent package replay
and actual PDF-page retrieval. Real 102-component summaries and file/image
identities agree; actual page inspected. Engineering acceptance remains pending.
See docs/MCP_TAGGED_NETWORK_DELIVERY.md.

A single tagged-network delivery command now executes finite label placement,
native DWG/PDF and independent source review on the real 102-component model.
The actual plot is inspected; complete engineering acceptance remains pending.
See docs/SOURCE_NETWORK_TAG_PIPELINE.md.

The102-tag drawing now passes actual AutoCAD DWG save/reopen/export and
fixed-scale PDF calibration; the rendered plot is visually inspected. Ten
annotation/native/layout checks pass. Full engineering remains pending.
See docs/SOURCE_NETWORK_TAGS.md.

Finite model-linked annotation now selects all102 source tags. Independent
graphic and saved-DXF checks pass; preview inspected. Tagged native DWG/PDF,
source ancestry and engineering acceptance remain pending. See docs/SOURCE_NETWORK_TAGS.md.

Source-native parameter schedules now cover102 components,223 owned ports and76
fitting paths with model-keyed identifiers, typed lengths, source flows and
explicit missing values. Independent numeric/HTML checks pass; drawing placement
and complete engineering acceptance remain pending. See docs/SOURCE_NETWORK_SCHEDULE.md.

The composed native-network delivery pipeline now has fixed-host MCP run and
independent-inspect access, returning pinned DWG/PDF paths for existing page
rendering. Engineering/visual scope remains explicit. See docs/MCP_SOURCE_NETWORK_DELIVERY.md.

Source-native projection, automatic review layout and native DWG/PDF delivery now
compose in one command, with independent native-source and PDF reconstruction.
Actual102-product/33-requirement execution and13 tests pass; engineering review
remains pending. See docs/SOURCE_NETWORK_DELIVERY.md.

Closed native-network contours now pass real AutoCAD DWG save/reopen and a
rendered, visually inspected fixed-scale PDF study sheet. All102 product IDs and
286 contours survive; seven native/workflow tests pass. Installation and complete
engineering acceptance remain pending. See docs/NATIVE_NETWORK_CONTOURS.md.

The verified source network now exports an editable GUID-linked XY silhouette:
102 native products, all33 requirements retained, independent saved-contour
area/bounds checks and inspected preview. Native DWG/plot and installation detail
remain pending. See docs/SOURCE_NETWORK_DRAWING.md.

MCP now provides bounded pages and exact directed-path detail reads for saved
native fitting requests, tied to the inspected record identity. Reads retain
missing evidence and do not replace source/native verification or design review.
See docs/MCP_FITTING_REQUESTS.md.

Native source-network and fitting analysis now have MCP run/independent-inspect
entry points through existing isolated workers. Source assumptions and incomplete
pressure/design acceptance remain explicit. See docs/MCP_NATIVE_NETWORK.md.

Native transition end straights now have a separate developed-flow friction
study through the existing equivalent-round/Fluids engine. It is not added to
pressure paths or source tables; taper friction, interaction and source inclusion
remain unresolved. See docs/TRANSITION_END_STRAIGHTS.md (repository root).

Latest transition source queries add eight conditional values, bringing the
represented network to31/76 finite paths;45 still lack numerical coefficients.
Source contraction caveats, physical review and complete pressure/fan acceptance
remain pending. See docs/TRANSITION_SOURCE_QUERIES.md (repository root).

Earlier milestone records follow; their counts describe those earlier runs.

Centred transition family checks now gate source-table lookup using both native
wall angles and source flow direction. Real-project screening finds nine geometry
candidates and22 unmatched transitions; no new coefficient or full pressure
acceptance is claimed. See docs/TRANSITION_FAMILY_CHECK.md (repository root).

Ten native rectangular bend paths now have source-bound conditional values with
explicit angle/Reynolds interpretation. The fresh study has 23 finite table
paths, 13 sparse-support requests and 40 unsupplied paths; all 76 remain explicit.
Full pressure, friction/interaction/product and engineering acceptance stay
pending. See DUCT_ELBOW_QUANTITIES.md.

The original fitting-table engine now consumes complete source/native analysis.
Of 76 fitting flow paths, 13 have conditional bounded table values, 13 need
unpublished support and 50 have no supplied table. All 31 native transition
requests and all original requirements remain. Physical applicability, friction,
interactions and complete pressure stay unresolved. See SOURCE_FITTING_DATA.md.

All 223 native ports now reconcile original design flows through the actual
saved network. Forty-five retained straight contributions and all 20 outlet
paths are checked; the absorbed common section's flow obligation survives.
Seventy-six loss paths across 57 fittings remain unresolved, so complete path
pressure, critical path and fan duty stay unknown. See SOURCE_NETWORK_ANALYSIS.md.

Native interface material now independently matches at all 101 actual links.
All 101 separately assumed bounded-region numerical proofs pass with nonempty
outside parts. Original raw clearance stays failed; numerical masks do not
establish product joints or installation/code acceptance. Pair summaries now use
physical IFC GUIDs (historical display-name undercounts corrected). See INTERFACE_CONTACTS.md.

An explicit compound construction revision now resolves the remaining represented
ROOT/J2 connections. The saved 102-body/101-link directed tree independently
replays, with zero raw intersections under unchanged policy. Clearance still
fails (101 records, 101 unique pairs). Absorbed sections/profile changes remain
explicit; pressure/loss, products, installation, architecture/equipment and full
agent/design acceptance are not established. See COMPOUND_JUNCTION.md.

The authored cross now integrates into a fresh native tee/elbow network with
103 bodies and 97 links. Raw intersection pairs reduce from ten to six under
unchanged policy; all remaining pairs associate with ROOT/J2. Clearance still
fails (99 records, 99 unique pairs). Full engineering and whole-agent acceptance
remain open. See SOURCE_CROSS_NETWORK.md.

Source four-arm junction coverage now includes a native cross/transition adapter.
J1 authors/replays as four components, ten ports and three internal links; J2
remains blocked on D-01. ROOT and all original requirements remain explicit.
This isolated candidate has not changed the parent network or its failed
coordination. See SOURCE_CROSS_CANDIDATES.md.

Fourteen source tee assemblies now integrate into a fresh trimmed network with
99 native bodies and 90 actual links. Independent source/native replay passes;
unchanged raw clash policy retains 10 intersection pairs and 93 unique clearance
violation pairs. ROOT and two multi-branch nodes remain unresolved. This partial
network is not complete installation or whole-agent acceptance. See SOURCE_TEE_NETWORK.md.

Source unequal-tee candidates now compile through native tee/transition tools
with both-end budgets: 14 local assemblies verify, one source node stays blocked.
They are not merged into the network; see SOURCE_TEE_CANDIDATES.md.

Native coordination failures now map to original unresolved source connections.
The real model has 38 unique intersection pairs at 17 unfinished nodes; all raw
failures remain. See DUCT_COORDINATION_DIAGNOSIS.md.

Finite supplied elbow-radius selection now reuses SciPy/HiGHS and existing
native IFC authoring. The real source study authors all ten equal-section elbows;
coordination still fails and remains explicit. See ELBOW_RADIUS_SELECTION.md.

AI clients can now prepare, execute and inspect the complete interpreted HVAC
package through MCP, using fixed host runtimes and existing PDF image delivery.
Actual real-project protocol execution passes; see MCP_HVAC_PROJECT.md.

The upstream writer and related requirement evidence now execute through the
complete existing HVAC package: native DWG, source-tree reviews and an actually
inspected 24-page report. Engineering gaps remain; see INTEGRATED_HVAC_REPLAY.md.

Source requirements can now link related calculation evidence beside their
primary review, preserving pending acceptance and all missing inputs. Actual
common-provider/project replay passes; see SUPPORTING_REQUIREMENT_EVIDENCE.md.

Optional upstream AutoCAD writing now participates in the original calculation
→ drawing → native task chain, with producer/source replay and failure blocking.
Real full-plan replay retains all pending reviews; see AUTOCAD_WORKFLOW_PROVIDER.md.

Shared `bsa autocad-source` and `bsa autocad-sheet` commands now reach the
existing verified AutoCAD adapters; fresh real sheet execution and installed-entry
checks pass. See PROJECT_CLI.md. Complete design acceptance remains pending.

Current user priority is AutoCAD and real assignment delivery; new Revit work is deferred. See [priority and upstream comparison](AUTOCAD_PRIORITY.md).

Workflow verification now binds recorded writer/task identity to the original plan,
closing an actually reproduced verifier-selection bypass. This preserves scoped
engineering/native/visual acceptance; see AUTOCAD_WORKFLOW_PROVIDER.md.

The whole agent is incomplete. Verified adapter execution and evidence consistency
must not be reported as autonomous professional design. The intended scope remains
requirements intake, CAD/BIM authoring, analysis, jurisdiction rules, iteration and
verified editable delivery across building services. No completion percentage is
claimed because this requires task-specific acceptance evidence.

| Area | Executed coverage | Remaining scope |
|---|---|---|
| Intake and host interpretation | Source-hashed passages, PDF images, explicit visual transcription, reviewed task/requirement handoff | General autonomous understanding of arbitrary briefs and complex drawings |
| AI interface | Local stdio MCP with project execution, committed reference resources, source/artifact reads and PDF page images | Named desktop-client setup and general deployment acceptance |
| Professional calculations | Existing bounded electrical, air/water network, fan/pump and other domain adapters | Applicability and missing evidence for each real assignment; no universal engine acceptance |
| CAD/BIM | Editable IFC/DXF; scoped native AutoCAD save/reopen and actual plot review | Arbitrary installation layouts, complete equipment/fittings/coordination and verified native Revit authoring |
| Cross-domain exchange | Source-bound water/pump/electrical shared identity and separate public multi-domain handoffs | Complete physical system integration across all MEP disciplines |
| Recovery | Explicit supplied pump/fan catalogues, original pump electrical checks and bounded mixed-graph replay | Arbitrary fault diagnosis, autonomous manufacturer research and parameter repair; complete physical/system acceptance |
| Regulations | Replaceable source-pinned Hong Kong rule packs and scoped checks | Complete Hong Kong statutory coverage and project-specific applicability |
| Review and delivery | Original requirement/evidence matrix, pending templates, scoped findings, byte/source/dependency checks | Complete engineering, numerical, native and visual acceptance for an actual project |

Some installed simulation/native runtimes have recorded host Application Control
failures. Their installation and interface code do not establish executed analysis;
retain each actual runtime result. Do not bypass host policy or transfer acceptance
from a different engine, build, model or run.

The upstream-backed 47-section AutoCAD schedule/arrow replay now also passes
native reopening and scoped A1 visual review; see [writer comparison](AUTOCAD_SCHEDULE_PROVIDER.md).
This remains a bounded task with all six project input gaps retained.

## Evidence entry points

- [Actual AutoCAD source intake](AUTOCAD_SOURCE_PROVIDER.md): native export plus pinned independent upstream reader on the real BSE3227 source; source interpretation and engineering gates remain open.

- [Source-to-engineering handoff](ENGINEERING_HANDOFF.md) and [shared CLI](PROJECT_CLI.md).
- [MCP tools and host setup](MCP_SERVER.md), [artifact reads](MCP_ARTIFACTS.md), [recorded PDF pages](MCP_ARTIFACT_PAGES.md).
- [Bounded recovery](RECOVERY_CONTROLLER.md) and [source-bound delivery review](DELIVERY_REVIEW.md).
- [Native shared-model drawing trial](COUPLED_NATIVE_HANDOFF.md) and [pump/electrical handoff](PUMP_ELECTRICAL.md).
- [Jurisdiction packs](REGULATION_PACKS.md), [Revit/MOOSAS findings](REVIT_MOOSAS_DIRECTION.md), [SWMM trial](SWMM_TRIAL.md).
- [Full scope and retained milestones](ROADMAP.md). Historical receipts keep their original method/source hashes; new code does not retrospectively validate old runs.

General tools and public synthetic tests belong in this repository. Real BSE3227
sources/runs belong in the separately selected polyu_bse3227 project. Coursework
replay is evidence for that scoped workflow, not proof of the whole agent. The
completed polyu_bse3124 project remains read-only historical context.

Next major acceptance needs remain general source interpretation, broader
cross-discipline physical design, applicable regulations, native delivery and
full-project review. Adding a tool entry alone does not satisfy them.
