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


## Draft window layout

The standalone driver now includes geometry-only window rectangles in each handoff. This is an explicit unapproved design choice: one centered rectangle on every vertical face of every space, with width and height fractions both sqrt(0.4). It is not a course-prescribed window shape. Assignment 5 pages 1-2 supply the generic 40 percent comparison WWR and allow selecting glazing type; they do not provide glazing U/SHGC/visible-transmittance ratings.

The thin adapter reuses thermal_windows rectangle coordinates and fit/interzone/overlap validation. An explicit require_glazing=False mode accepts geometry-only rows with no glazing field. All simulation authoring and audits retain the default require_glazing=True; incomplete drafts cannot pass as complete thermal inputs. No new engine/dependency or fabricated optical/thermal rating is introduced.

Actual runs/public-concepts-v5 produces 8/8/16 rectangles for compact/slender/stacked, with total draft area 476/532/672 m2 respectively, matching the target budgets. Seven concept tests and the existing sourced-window input validation test pass, including missing-glazing rejection and oversized draft rejection. The previous area/contact controls also remain passing. Evidence: evidence/document-intake/public-window-layout.json.

These are JSON layout rectangles with world vertices, not IfcWindow elements, cut wall openings, saved OSM subsurfaces or a validated daylight scene. modeled_window_area_m2 remains zero (native authored area), glazing_selected=false and thermal_model_ready=false. Existing IFC previews continue to display the concept space boxes only. Materials, thickness/frame details, site shading, glazing selection and actual simulation remain pending.


## Unified workflow layout integration

A `bim` task with the explicit concept-space scope may now supply `concept_layout`, a repository-local JSON settings file containing exactly source, window_wall_ratio and layout. Supported layout is centered-equal-fraction only. The existing workflow inventories the settings and all reused geometry/layout module sources, authors/reopens the IFC, then runs the same layout composition against that exact saved model and original source. The output is `<task>/concept-layout/geometry-handoff.json`, covered by workflow artifact hashes. This supersedes the earlier standalone-only integration limit; standalone and workflow now share bsa.concept_layout rather than importing a benchmark script as a library.

Re-run the --source-cache command above to include layouts in all three concept tasks. Actual runs/public-concept-workflow-v3 has three passing concept tasks with 8/8/16 draft windows and all 34 technical interpretation tasks pending. No obligation was removed. Settings, source geometry and IFC hashes are retained in each handoff. Full workflow source/artifact integrity passes; design acceptance remains false.

Seven concept tests and two actual workflow tests pass. Controls reject boolean WWR, missing source, unknown layout and nonconcept scope before execution; changing a saved handoff invalidates workflow integrity. There is no new simulation engine or dependency, and successful draft-layout execution cannot establish glazing selection, authored openings, energy/daylight results or full assignment acceptance. Evidence: evidence/document-intake/public-layout-workflow.json.


## Native concept walls and openings

`bsa.concept_facade` now makes a separate IFC revision with real IfcWall, IfcOpeningElement and IfcWindow relationships. It rederives the layout from the saved source IFC and original geometry/settings, rather than trusting an edited handoff. Existing pinned IfcOpenShell 0.8.5 APIs author wall-like extrusions and void/filling relations. Window bodies are explicitly solid box envelopes, with no inferred frames, glazing properties or product selection. Upstream window representation defaults were not used because their frame dimensions would otherwise be unsourced.

Provide explicit thickness decisions via benchmarks/mit-4401-2018/facade-decisions.json. The current 0.2 m wall and 0.04 m window-envelope thicknesses are unapproved concept choices, not measured construction or glass specifications. Walls extend outboard of concept space faces; corners are not joined/detailed, and slabs/roof/partitions remain absent. Floor-to-floor massing is not established as a clear thermal air volume.

Example after generating the public concept workflow:

```powershell
.venv/Scripts/python -m bsa.concept_facade --ifc runs/public-concept-workflow-v3/workflow/concept-compact/model.ifc --project runs/public-concept-workflow-v3/compact.json --layout runs/public-concept-workflow-v3/compact-layout.json --basis benchmarks/mit-4401-2018/facade-decisions.json --out runs/new-native-facade
```

The saved revision preserves every original STEP entity record, schema/EXPRESS validation passes and source hashes remain unchanged. Independent saved checks require stable IDs, original source metadata, exact wall/window/opening counts, host/fill/storey relationships, metre-space geometry, wall bounds, all 16 outer/reveal corner vertices, closed consistently wound through-hole topology (Euler zero) and net material volume after subtracting the opening. Window/opening solids must match expected bounds/depth/placement, with explicit native window width/height. This verifies actual native Boolean subtraction, not simply a window box over a solid wall.

Actual runs/public-facades-v1 produces 8/8/16 wall-opening-window groups for compact/slender/stacked. Opening areas are 476/532/672 m2. Three tests pass over all variants, source preservation and rejection controls (removed void/fill relations, changed window width, GUID/source and invalid thickness). Evidence: evidence/document-intake/public-native-facades.json.

Stacked assembly and isolated-wall previews were actually inspected. The full assembly shows the storeys but opaque window-envelope bodies hide holes in filled elevations, with distracting triangulation shading. The isolated wall clearly shows the through opening. Previews are not native BIM GUI review, CAD drawings or architectural acceptance. This separate revision is currently standalone, not yet an inherited unified workflow producer. Materials/products, corner interfaces, room program, site shading, actual performance simulation, MEP and full delivery remain pending; design_accepted and thermal_model_ready stay false.
