# Reduced-branch sharp tee study

The existing source construction first enlarged each branch to the main-core
section and then tapered back to the scheduled branch. The equal-area sharp
branch queries lack populated ASHRAE2021 Fitting5-28 support. Changing an engine
cannot supply those missing cells. Reuse review found that hvac-pressure0.1.1
requires a rounded r/Wb=1 branch, unlike this sharp construction; FreeCAD/OSE
has not established an applicable rectangular authoring route. Existing pinned
IfcOpenShell0.8.5 ShapeBuilder/Boolean APIs and Manifold3D3.5.4 already execute
the required geometry operations. No new kernel, solver or dependency is added.

`bsa.unequal_rectangular_tee` is a thin, separately scoped revision adapter.
Its source JSON has exactly `tee` (the original sourced rectangular-tee fields)
and `branch_section_m` (two positive clear dimensions). Both branch dimensions
must fit within the main section and at least one must be smaller. Section,
gauge, nominal/internal interpretation and placement remain classified inputs.
The main half length and branch length must satisfy the original tee validator.

```
python -m bsa.unequal_rectangular_tee run PROJECT --out NEW_RUN
python -m bsa.unequal_rectangular_tee verify NEW_RUN
```

Use explicit host BSA_PROJECT_ROOT for external project work. The original equal
tee author produces a separately retained template, then its existing geometry
APIs replace only the new copy's body with distinct main/branch prism unions.
Saved checks inspect every actual extrusion/profile/frame, owned ports, source
properties, schema/EXPRESS, connected wall material, independent inclusion-
exclusion volume, Euler characteristic-2 and both through-bores. Verification
requires exact source/method/runtime pins and preserves design_accepted=false.
The adapter does not reclassify the original equal-tee outputs.

The actual source-linked local study uses13existing branch sizes and extends
each new branch reach to the old taper's external end. Native end-frame checks
preserve that endpoint and the two main-core frames. Each local candidate
removes one separate branch taper; original main-arm tapers remain separate.
Thirteen actual saved IFCs verify. Only TAP-VAV-04 enters the original source
table's populated support. Its source-port flow ratio and revised velocity
ratio are independently recomputed; separately transcribed four-cell Decimal
arithmetic agrees with the existing SciPy bounded lookup and inlet pressure
reference. Other branches remain unsupported, without extrapolation.

This does not prove lower pressure: the old branch loss was unknown. The new
value remains a conditional local dynamic contribution, excluding whole-fitting
friction/stations, close-fitting interaction and installation applicability.
No parent network is modified and its original45numerical gaps remain.
Full-network merge/reanalysis/coordination is a required next step.

The selected node's saved-IFC projection reuses existing source_network_drawing,
ezdxf and ifc_native. A separate local A4at1:10 sheet undergoes actual AutoCAD
save/reopen and plotted-reference verification. Initial overlap was found in
the actual PDF and corrected before delivery. This is an isolated plan study,
not a complete assembly, fabrication or installation drawing. Source tables,
private project geometry and runtime detail are not published here.
