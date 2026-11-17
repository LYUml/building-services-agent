# Candidate gate audit

Follow-up: the older full run is now terminal and failed: 1,827 tests,
12 failures, eight errors, 258 skips. Its receipt/source hashes verified.
Platform-specific native library paths and external installed method-file
boundaries are being repaired, without removing checks. See
[diagnosis and current recovery scope](FULL_REGRESSION_RECOVERY.md).
Corrected targeted/full CI and final candidate handoff remain pending.

Checkpoint: implementation `9390a92`. This audit keeps the complete requested
candidate objective; it does not substitute a smaller successful workflow.
Candidate completion is not yet proven. No release/tag or user acceptance.

| Required result | Inspected evidence | Current finding |
|---|---|---|
| Support scope and host boundaries | CANDIDATE_SUPPORT.md; actual MCP SDK catalogue/source-routing audit; clean stdio execution | Documented and executed within stated platform/profile scopes; arbitrary autonomous design is not claimed |
| Clean installation and repeatability | CLEAN_CANDIDATE_INSTALL.md; new public Git clone and environment; second constrained installation; pip check and doctor | Native HVAC/MCP profile executed; 42 dependency pins reproduce 44 installed distribution versions on Windows/Python 3.12 |
| Matching CI and release checks | core.yml and check.yml; observed Actions jobs | Five core/profile jobs passed at a6236c3; six domain jobs passed at 4e5e028. Full-regression job 133969615693 is still executing; final outcome and skip/failure review remain open |
| Actual project revision propagates | REAL_PROJECT_REVISION.md; real-project-revision.json; independent package inspection and actual AutoCAD plot review | 44 changed sizes across 47 sections; 235 drawing cells; unchanged flows and 20 VAV group table; 388 report rows checked. Manufacturer equipment selection and full engineering acceptance remain separate |
| MCP control coverage | check_mcp_contract.py; actual SDK catalogue and 40 unknown-field rejection calls; clean six-call native stdio session; domain protocol evidence | 40 tools map to 39 fixed operations. This is route/schema and scoped execution proof, not every possible task/input combination |
| Modularity, startup, memory and disk improvement | worker_transport.py; lazy recovery imports; worker-transport-memory.json; ci-bootstrap-lazy-recovery.json; hvac-light-profile.json | Diagnostic stress parent peak 156.31 to 60.18 MiB; pump import peak 101.23 to 28.56 MiB; median import 0.513 to 0.042 s; selected HVAC dependency disk reduction 25,558,050 bytes. These have distinct measured scopes |
| Reuse, engineering/source constraints and history | REUSE_SURVEY.md; retained upstream pins/notices; source-bound inspection; unchanged original 19 input hashes; separate coursework repository status | Existing upstream engines retained, no invented design/code acceptance; private project sources and runtimes excluded from candidate snapshots |
| Coherent commits and candidate artifact | configured origin HEAD; source-candidate CI step and receipt; SOURCE_CANDIDATE.md | Changes pushed without release. Same-platform archive reproducibility and retained review artifact observed; final candidate entry must cite its exact revision |
| Final user acceptance handoff | This audit and remaining regression gate | Pending. Do not mark the goal complete or infer acceptance before the remaining gate is resolved and the actual candidate/limits are handed over |

The full-regression job remains authoritative even though narrower jobs passed.
It must reach a terminal state, then its receipt/log, actual test counts,
failures and skips must be inspected. A collection count, artifact presence or
elapsed time cannot replace that result. Do not restart solely because a log
endpoint is temporarily unavailable while the same job remains live.

Existing native/public evidence remains associated with its executed source
revision. Subsequent documentation and constraint-file changes do not authorize
editing old method hashes or relabelling old results. Scoped engineering limits
(ADPI applicability, complete pressure, physical installation and jurisdiction
acceptance) remain explicit; no user-approved requirement has been removed to
obtain a green software result.
