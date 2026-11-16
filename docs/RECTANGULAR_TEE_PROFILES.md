# Native sharp-tee section reader

`bsa.rectangular_tee_profiles.sections(obj)` reads the existing equal/reduced
rectangular sharp-tee authoring family using pinned IfcOpenShell 0.8.5 and NumPy
2.5.4. It checks metre units, the actual outer-minus-inner two-prism unions,
uniform wall thickness, profile frames/depths and all three relative port frames.
Branch dimensions come from the branch bore profile, not the main bore profile.
Crosses and compound junctions are outside this family and are rejected.

`canonical_case(model, case, product_guids)` requires an explicit unique tee
selection and reconciles every literal section with the independent material-cap
dimensions in the supplied analysis. It returns a separate case with canonical
velocities and dynamic pressures. It does not modify saved IFC or source flows.
The supplied analysis still needs its own native/source verification; this is
not a substitute for the existing network verifier or a registered MCP producer.

The actual saved BSE3227 network executes this reader for 14 tees/42 ports at
maximum and given minimum flow. All existing conditional results match to the
declared relative numerical check, with nulls retained: 30 conditional paths
and 33 numerical gaps. No new coefficient or pressure-saving claim follows.
The older method-bound source-network modules and receipts remain unchanged.

Validation: `python -m unittest tests.test_rectangular_tee_profiles -v` runs
actual native authoring with a rotated fitting, distinct branch sizes, immutable
input checks, and rejection of material-cap mismatch, duplicate selection,
altered wall profile and displaced port. Project replay evidence remains private
at `07_Agent_Work/runs/reduced-branch-network-reviewed/canonical-tee-profile-replay-reviewed`.

This is a thin adapter over already reused engines, with no new dependency or
solver. Physical applicability, installation and complete pressure acceptance
remain unresolved. General revision production and MCP registration are pending.

## Source-network calculation integration

`source_network_analysis.calculate(..., native_tee_guids=[...])` now accepts an explicit unique selection of supported native tee GUIDs. It reuses `sections` before port-flow calculation and requires each literal bore to match the independently tessellated material cap within the existing 1e-8 m bound. It uses the literal dimensions for flow velocity and subsequent table queries; strict correlation bounds are unchanged. No implicit object-name selection or rounding/clamping is introduced. Unsupported profiles or mismatched caps fail. Default callers retain the existing mesh-cap route. This is a Python calculation option, not an added CLI/MCP argument; geometry quantities for other fitting families still require their existing adapters.

Actual current118body IFC execution selects13tees and reads255ports in both flow cases without copying prior port dimensions. All88 conditional table paths reproduce the reviewed values within8.39e-13Pa. This eliminates three spurious out-of-range queries caused by mesh-recovered area ratios0.8000000000000114 at an exact source0.8 endpoint; it does not validate extrapolation or resolve the four compound paths. Five focused tests pass, including duplicate selection and material-cap mismatch rejection. See evidence/native-tee-network-calculation.json.
