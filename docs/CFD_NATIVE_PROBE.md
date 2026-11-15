# Saved native CFD line probes

`python -m bsa.cfd_native_probe --spec RELATIVE_SPEC --output NEW_RELATIVE_REPORT`
extracts actual saved SU2 node values on a declared line. The host must set
`BSA_PROJECT_ROOT`; specifications cannot select a workspace. The JSON spec has
`mesh`, `field`, `start_m`, `end_m`, `fields` and optional `tolerance_m`.
All paths remain within the selected project. Existing reports are preserved.

The adapter binds every saved point identifier and coordinate to the complete
three-dimensional, single-zone mesh. It rejects duplicate/missing/foreign nodes,
nonfinite requested values, incomplete rows and changing input observations.
It does not interpolate, extrapolate, prove mesh-edge connectivity, normalize
experimental data or accept convergence/engineering. Native endpoints need not
coincide with the declared segment endpoints.

Four focused tests pass. Actual CLI execution on the official Sudo bend mesh
and a saved SU2 field extracts 40 native nodes on the upstream sampling line.
Output-preservation and host-boundary controls execute separately. See
[execution evidence](evidence/cfd-native-probe.json). Raw fields stay private.

Reuse: Python CSV parses native SU2 output; no flow engine is copied. The line
comes from the official [tutorial postprocessor](https://github.com/su2code/Tutorials/blob/ce41729be812da70f06bea0fd1a97a6ce4da14aa/incompressible_flow/Inc_Turbulent_Bend_Wallfunctions/paraview_extract_linedata.py).
The Tutorials repository is pinned to that commit and its LGPL 2.1 notice is
retained with the private inspected inputs. This adapter does not execute the
ParaView script. The official benchmark has 27 experimental velocity points;
its supplied inlet profile maps to all 618 inlet nodes. Experimental inlet,
normalization and physical correspondence remain separate checks.

The source smooth circular-bend wall-function case is different from the
project's rough rectangular, wall-resolved model. A reproducible two-thread
access violation and successful three-step serial control are retained; serial
baseline computation continues. Neither startup nor this probe accepts the
benchmark experiment or BSE3227 full pressure. No new MCP registration is claimed.
