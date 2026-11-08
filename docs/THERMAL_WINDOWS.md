# Sourced thermal windows and solar results

Optional `building.windows` adds declared vertical exterior-wall rectangles and explicit simple glazing to the thermal model. Existing opaque constructions, annual weather, internal gains and ideal-load/PTAC analysis continue unchanged. Saved IFC spaces can supply the room geometry; window geometry/performance is independently declared and sourced. This feature does not invent architectural IFC windows or modify the source building model.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/thermal-windows-plan.json --out runs/thermal-windows --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/thermal-windows
```

The example uses four explicitly synthetic windows and existing three-space/PTAC inputs. Its source IFC has thermal-space envelopes, not architectural wall/opening products. No measured building dimensions, manufacturer glazing or product/code performance is claimed.

## Inputs and geometry

Each window requires exact fields `id`, `zone`, `source`, `face`, `offset_m`, `sill_m`, `width_m`, `height_m`, `glazing`. IDs are case-insensitively unique ASCII identifiers. The face is one of `X-`, `X+`, `Y-`, `Y+` in model Cartesian coordinates; it is not an inferred compass direction. Existing explicit building north axis governs the engine's solar orientation separately.

Offset is measured from the zone's minimum horizontal coordinate along the selected wall: positive Y for X faces and positive X for Y faces. Sill is above that zone's floor, including its actual floor elevation. Width/height and offsets must be finite positive numbers. Windows must fit strictly inside the wall (geometric comparison tolerance 1e-7 m); touching external wall edges is outside this supported contract. This is a geometric restriction, not a fabricated frame or construction dimension. Positive-area overlaps are rejected. A source rectangle on an adjacent interzone wall is rejected.

When room dimensions come from IFC, the planning validator initially checks window fields and zone IDs without using its temporary geometry fixture for window fit. Full fit/exterior checks run after actual saved IFC geometry is read. Authoring then requires exactly one actual exterior parent wall, transforms world vertices to the native space coordinates and verifies outward face orientation. Unknown/ambiguous parents fail rather than becoming assumed exterior glazing.

`glazing` requires `source`, `u_factor_w_m2k`, `shgc` and `visible_transmittance`. The inspected EnergyPlus 25.2.0 `WindowMaterial:SimpleGlazingSystem` IDD requires positive U-factor and SHGC/visible transmittance strictly between zero and one. U-factor includes surface film coefficients; it is not the inverse of the bare-layer resistance reported for opaque materials. The [official glazing model reference](https://energyplus.readthedocs.io/en/stable/guides/input-output-reference/1.9-group-surface-construction-elements.html) describes this as a system-index model rather than a physical layer stack. The existing pinned IDD hash is recorded in `window_audit.validation_basis`; SDK/engine checks remain applicable beyond individual field ranges.

Each window is an explicit `FixedWindow` with multiplier one and one `SimpleGlazing` construction layer. Explicit frame/divider and shading controls are absent and audited; daylight controls are not added. Effective source indices may describe system-level performance, but no physical frame, gas gap, glass stack or manufacturer geometry is inferred. Detailed spectral/angular/product applicability and real source verification remain pending.

## Saved model checks

The base builder and final annual save are reopened. Audits verify exact names/counts, parent boundary/type, zone, world vertices, outward normal, type/multiplier, explicit glazing assignment, U/SHGC/visible values and geometry/material source features. Frame/shading/default-construction additions fail. World-coordinate tests cover all four faces in a translated elevated space.

Window gross area must match width × height. For each parent wall, gross area minus opaque net area must equal its window area. Opaque construction audits retain `role_area_m2` as gross parent-surface area and now additionally report `role_net_opaque_area_m2`; window area is not silently treated as opaque wall. The example has 6.48 m² total windows and 131.52 m² net exterior opaque wall from 138 m² gross wall.

## Native annual quantities

Actual EnergyPlus hourly outputs are retained for each exact window identity: transmitted solar energy J, window heat gain J, window heat loss J and incident solar W/m². Extraction checks one weather environment, the full declared calendar, year/hour/interval, units, finite nonnegative values and complete unique series. Raw `window-hourly.csv` preserves these native units.

Hourly J integrates to kWh using 3.6 million J/kWh. Hourly average incident W/m² × actual window area integrates over one hour to incident kWh. Monthly sums reconcile with annual sums. Transmitted solar cannot exceed incident solar on that window within the sourced rate tolerance; this is a numerical bound, not a complete heat-balance validation. Window heat gain/loss contain more than transmitted solar and must not be added to it as independent whole-building energy. See the [official window output definitions](https://energyplus.readthedocs.io/en/stable/guides/input-output-reference/1.10-group-thermal-zone-descriptiongeometry.html).

`summary.windows` reports per-window annual/monthly thermal/solar quantities, separate from HVAC electrical energy. Native tests reduce SHGC while holding other inputs unchanged and verify lower actual transmitted solar for every window. This does not imply a net annual electrical saving: heating, cooling, system and control effects still require actual analysis. Supplying visible transmittance does not establish daylight illuminance or automatic lighting savings.

The current feature supports vertical, axis-aligned, rectangular exterior windows. Interior windows, curtain walls touching parent edges, skylights, arbitrary/sloped geometry, explicit frames/dividers/shades, physical glazing layers, automatic IFC architectural authoring, daylight/glare controls and full engineering acceptance remain pending. Existing source, material, equipment, native completion and unmet-time gates remain in force.
