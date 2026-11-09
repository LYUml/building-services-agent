# Continuous cable native geometry trial

Executed 2026-11-10 using pinned IfcOpenShell 0.8.5 and the existing Manifold mesh validator. This is a synthetic geometry probe, not an engineering design or registered workflow capability.

`scripts/probe_cable_union.py --out <new repository directory>` creates a quarter-circle envelope (centreline radius 0.3 m, envelope radius 0.01 m) and a tangent 2 m straight, all explicitly assumed. The existing revolution probe supplies the first solid. Upstream `geometry.add_boolean` performs UNION; no custom triangles, mesh repair, contact waiver or tolerance widening is used. The independent expected centreline length is 2.471238898038469 m. Analytic volume, volume-weighted centroid and tight bounds are compared to the saved, reopened native tessellation using existing tolerances.

Actual execution: `runs/cable-union-probe-v1/probe.json`. IFC schema/EXPRESS validation, positive oriented single-connected-solid validation, volume, bounds and centroid checks passed. Measured volume was 0.0007763485753805562 m³. This establishes only this tangent union, not arbitrary routes or physical distribution joints.

Reuse: [official IfcOpenShell add_boolean API](https://docs.ifcopenshell.org/autoapi/ifcopenshell/api/geometry/add_boolean/index.html). Existing repository upstream attribution/licenses remain applicable. The installed 0.8.5 lacks the documentation's suggested `validate_csg` helper; the probe explicitly assigns standard CSG representation and executes full saved schema/EXPRESS validation instead. No dependency was upgraded.

Pending: independent composite Axis, source-driven piece contracts, endpoint/tangent/profile checks, ports, saved electrical length extraction, bend-limit coverage, numerical/workflow integration, negative controls and visual review. The old multi-cable distribution-node clearance failure remains a failure: a loaded intermediate board cannot be replaced by an uninterrupted cable to hide missing hardware.

## Independent Axis follow-up

The updated probe now saves an independent `IfcCompositeCurve`: exact three-point circular ArcIndex followed by a two-point line. Forward segments declare CONTSAMEGRADIENT at the internal join and DISCONTINUOUS at the open end, following the [official segment contract](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/schema/ifcgeometryresource/lexical/ifccompositecurvesegment.htm). The read-only `bsa.cable_continuity.inspect` verifies the exact two-operand UNION, separate Body/Axis correspondence, coincident endpoints, same forward tangent and equal circular profile radii. It derives true length, endpoint outward normals and analytic combined properties. Native one-solid and analytic-volume checks remain mandatory in the probe; the inspector alone does not prove native Boolean execution or absence of overlap.

Actual `runs/cable-union-axis-probe-v1` passed saved schema/EXPRESS, connected native solid and both independently fixed-fixture and Axis-derived volume/bounds/centroid comparisons. Six tests passed, including altered Axis endpoint, disconnected Body plus Axis, unequal profiles, false transition and reversed sense. Upstream EXPRESS emits an unclosed-file ResourceWarning; validation still completed. Evidence: `evidence/pandapower/cable-union-axis-probe.json`.

This supersedes only the independent-Axis and scoped correspondence items above. Source-driven authoring, ports, electrical-reader registration, bend-limit coverage, numerical/workflow integration and visual review remain pending. Existing electrical readers continue to reject this unsupported composite body, preventing premature release.

## Saved electrical reader integration

The electrical reader now accepts this exact one-quarter-then-tangent-straight UNION through the same inspector and mandatory native single-solid/analytic checks. It checks both endpoint port positions and outward normals, bus-anchor correspondence and numerical length. The new route_geometry value is `quarter plus tangent straight`; it contains exactly one supported bend, and cable_bend_limits requires that line's bend basis rather than dropping it from coverage. Source inventory includes the new inspector module. General nested unions and additional pieces remain unsupported.

Four executed integration tests verify saved native geometry and ports, rejection of an incorrect end-port normal, rejection of omitted composite bend coverage, and fresh project derivation from a deliberately stale chord length. The original project is unchanged. This proves geometric length derivation, not a freshly solved electrical study or end-to-end drawing workflow. The earlier standalone-only statement above is historical; source-driven authoring, a solved workflow/native drawing, visual review and full engineering acceptance remain pending.

## Reproducible source author and numerical execution

`author_three_phase_ifc_fixture.py` now supports `--body-kind quarter-straight`. Its synthetic geometry contract adds `tangent_extensions_m`, with exact coverage of quarter_bends and positive finite SI extension lengths. The independently supplied bus anchors and project lengths must match the complete route before authoring. The shared author uses standard IFC revolution, extrusion, UNION and composite curves through pinned IfcOpenShell; it does not triangulate or repair a mesh. Stable element/port identifiers and source hashes use the existing fixture machinery. This remains a synthetic fixture author, not arbitrary brief-to-model design.

Run `.venv/Scripts/python scripts/run_continuous_cable_demo.py --out runs/new-continuous-study --python tools/pandapower-runtime/Scripts/python.exe`. It stages explicit assumptions in a new repository folder, retains the 2-bus terminal-load topology, supplies a separate geometry-based length_source, authors the native cable and derives a new project before fresh pinned pandapower execution. Actual `runs/continuous-cable-study-v2` passed geometry correspondence and numerical verification/targets with design_accepted=false. The first run was retained as a rejected axis-type mismatch; the author now explicitly creates the supported two-point IfcPolyline rather than relying on ShapeBuilder's default indexed curve.

The current seven continuity tests cover source-author roundtrip and invalid extensions as well as native geometry/mutation checks. A dedicated solved-workflow/native drawing run, full visual review, manufacturer selection and installation/regulatory acceptance remain pending.
