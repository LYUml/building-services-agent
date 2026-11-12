# Modular native straight-friction analysis

The trusted provider `fluids.native-stub-friction` implements capability
`analysis.air.native-stub-friction` and payload
`bsa.straight-friction-components/1`. It wraps the existing native stub reader
and pinned fluids 1.3.1 (MIT); no new pressure solver or dependency is added.
IfcOpenShell and the existing source-model verifier retain their attribution.

A standalone module request requires exactly `stubs` and `basis` source roles.
The former identifies verified terminal-stubs.json; the latter supplies only
source-classified viscosity and roughness. Coordinate frame must match the
original room balance. Dimensions, endpoints, flow and density are inherited
from the exact verified native/source chain; callers cannot replace them.

A workflow `module_analysis` task may depend on `spatial_terminal_stubs`.
Its request template contains only `basis`; the workflow materializes the exact
upstream report path/hash. For the existing source-only plan builder, supply
`--stub-basis` and `--friction-basis`. Existing workflow verification and
source-context validation recheck this binding and provider disable selection.

The common payload preserves units, maximum/minimum cases, native identities,
source classifications, fluid basis and a hashed report reference. Numerical
`pass` means all individual straight-friction cases calculated. Engineering
acceptance stays pending, fully-developed-flow verification and whole-system
pressure completion stay false. Transitional flow retains unknown friction.
Short-stub development, actual joints/openings, pressure losses and fan duty
remain unresolved. Parallel branch pressure components are not summed.

Executed evidence: native and MOOSAS geometry-provider chains, analysis-disabled
and geometry-disabled workflows are recorded in
`evidence/modular-stub-friction.json`. These are explicitly synthetic studies,
not the BSE3227 coursework and not a complete engineering design. Only one
pressure provider is implemented; a second pressure engine is not verified.
The unchanged coordination policy retains interface failures and final review.

Validation: 34 related tests pass (22 contract/inheritance/module/status, one
actual native-provider integration and 11 friction/network regressions).
IfcOpenShell emits an upstream unclosed-rule-file ResourceWarning; tests pass.
Validation covers strict typed payloads and status/unit/frame/identity/path
controls, exact inherited source binding, actual native-model projection,
provider disabling and rejection of fabricated engineering acceptance. Existing
module and workflow-status regressions also run. See SPATIAL_STUB_FRICTION.md
for the underlying method, numerical tests and physical limitations.
