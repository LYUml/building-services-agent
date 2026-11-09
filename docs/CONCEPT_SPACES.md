# Source-linked concept spaces

The public MIT 4.401 benchmark now has three explicit, unapproved massing decisions. The compact 50 x 35 m / two-storey, slender 70 x 25 m / two-storey and stacked 35 x 25 m / four-storey options each total 3500 m2 gross footprint. These are chosen dimensions, not measured areas. The 3.5 m floor-to-floor height is not clear height. Local orientation is provisional; no site is georeferenced. Course comparison WWR 0.4 is not represented by windows.

Reuse: existing pinned IfcOpenShell 0.8.5 authoring, box-mesh inspector and Matplotlib preview, through the existing workflow `bim` task. No new solver/dependency. Upstream versions/licenses remain in the reuse survey and lockfiles. Course attribution and educational material licensing remain separately recorded in benchmarks/mit-4401-2018; generated environments and source PDFs are not committed.

Run standalone geometry and preview:

```powershell
.venv/Scripts/python scripts/run_public_massing.py --out runs/new-public-concepts
```

Run the reviewed-source partial workflow (cache contains the five hash-pinned official PDFs):

```powershell
.venv/Scripts/python scripts/run_public_massing.py --out runs/new-public-concept-workflow --source-cache runs/public-brief-intake-v1/sources
```

The explicit `axis-aligned concept space envelopes` scope requires sourced storeys, matching elevations/heights, nonoverlapping source volumes and gross-footprint basis. Empty MEP systems/devices are permitted only here: fake equipment is forbidden. Saved IFC checks cover native closed box geometry, metre units, exact space/storey counts, hierarchy, actual storey placement/elevation, stable IDs and source properties. Preview inventory includes spaces and elements, preventing hidden omitted MEP context. Original MEP scope still requires real system/device inputs.

Executed: runs/public-concepts-v3 produces three native models and previews with model_checks_pass=true. runs/public-concept-workflow-v2 gives three passing geometry tasks and retains all 34 pending technical interpretation tasks; design_accepted=false. Twelve related tests passed; the four concept tests passed again after adding storey-source and storey-placement mutation controls. Evidence is in evidence/document-intake/public-concept-spaces.json.

The stacked preview was visually inspected: outer shape and axes are legible, but shared coplanar space faces produce triangle shading and storey boundaries are not visible. This is a geometric preview, not architectural drawing acceptance. Native checks establish the individual storeys; the image alone does not. Site selection, facade/windows, net/program areas, thermal boundaries, daylight/energy, MEP design, native CAD drawings and full deliverable acceptance remain pending. This partial course workflow is not either of the two required completed independent real assignments.


## Saved geometry handoff

The standalone driver also writes `geometry-handoff.json` beside each IFC. It reuses `thermal_binding.extract`, `thermal_geometry.boxes` and `adjacency` after independently checking the concept source against the saved IFC. It uses actual native solid coordinates and complete GUID coverage; no copied area metadata or new geometry engine is used. Source bytes are checked before/after extraction.

Actual runs/public-concepts-v4 gives compact/slender/stacked exterior vertical face areas of 1190/1330/1680 m2, exposed top and bottom face areas of 1750/1750/875 m2, and one/one/three shared horizontal contacts. Subtracting both sides of each contact avoids counting internal faces as exterior. These are geometric areas of the chosen boxes, not surveyed facades or net building areas. Applying the separately sourced course 0.4 WWR yields target glazing areas of 476/532/672 m2; modeled window area remains zero. No window placement, glazing rating, energy saving or daylight result is inferred.

Six concept tests pass, including independent analytic surface/contact expectations and changed-native-geometry rejection. The handoff remains thermal_model_ready=false. Boundary interpretation (including floor-to-floor versus air height), site/weather/orientation, construction, glazing, gains/schedules and HVAC are unresolved; OpenStudio/EnergyPlus runtime blocking remains unchanged. The unified workflow continues to provide concept geometry only; this extra handoff is currently emitted by the standalone driver, not a new completed simulation task. Evidence: evidence/document-intake/public-concept-thermal-geometry.json.
