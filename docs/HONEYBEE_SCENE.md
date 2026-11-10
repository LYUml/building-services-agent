# Saved IFC to Honeybee Radiance concept scenes

This thin adapter reuses upstream Honeybee Radiance 1.66.304, Honeybee Core 1.64.83 and Ladybug Geometry 1.35.7, with all seventeen installed dependencies pinned in adapters/honeybee-scene/requirements.txt and dependencies.json. The public APIs author rooms/apertures, solve adjacency, generate sensor grids, validate/reload HBJSON and export Radiance geometry/materials. No Radiance binary or annual recipe is launched.

The adapter worker is explicitly AGPL-3.0-only, with the upstream Honeybee AGPL license and installed dependency license/notice texts retained under adapters/honeybee-scene. This is an isolated local subprocess integration, not a relicensing of upstream code as repository-original permissive code. Source environments remain ignored. See THIRD_PARTY.md.

Restore the environment with:

```powershell
./adapters/honeybee-scene/bootstrap.ps1
```

After generating the reviewed public concept workflow, copy benchmarks/mit-4401-2018/scene-decisions.json into that project directory as scene-basis.json, beside its sources directory. Run:

```powershell
.venv/Scripts/python -m bsa.honeybee_scene --ifc runs/public-work-plan-v2/workflow/facade-compact/facade.ifc --project runs/public-work-plan-v2/compact.json --layout runs/public-work-plan-v2/compact-layout.json --facade-basis runs/public-work-plan-v2/facade-basis.json --scene-basis runs/public-work-plan-v2/scene-basis.json --out runs/new-honeybee-compact --python tools/honeybee-scene-runtime/Scripts/python.exe
```

The host rechecks the actual saved native facade against original source geometry/layout/thickness settings before passing a bounded packet to Honeybee. Source documents, input files, runtime executable, worker and dependency pins are hashed before/after. Source PDF changes, invalid fractions/sensor settings or native window mutation reject. The generated packet is also checked for changes during execution.

Assignment 5 page 2 supplies 0.5 wall / 0.2 floor / 0.8 ceiling reflectances and upward sensors at 0.85 m with 0.5 m spacing. Assignment 8 page 3 baseline VLT 0.70 is explicitly selected for this A5 concept scenario; it is not a supplied A5 glazing requirement or a manufacturer rating. No SHGC or U-value is needed or inferred for this optical-only conversion. Ground reflectance, site, obstruction geometry and detailing remain unresolved, rather than silently using a complete generic scene.

Saved HBJSON checks cover room area/volume, exact aperture world vertices/host/area, assigned optical properties, complete paired adjacency and exact upward grid positions/counts. This adapter currently accepts rectangular dimensions that divide into integer grid cells, rejecting an unsupported edge-grid interpretation. It then independently reads the emitted Radiance primitive records, verifies aperture coordinates and polygon coverage, and checks actual punched opaque wall areas. Unused generic modifier definitions emitted by upstream remain in materials.rad; actual geometry is required to reference only the explicitly assigned BSA modifiers.

Two upstream numerical details are recorded, not hidden by loose tolerances. Honeybee converts source transmittance 0.70 to Radiance glass transmissivity 0.7628419848230164; these are different quantities. Its approximate inverse reports 0.7007609041186985 using a 0.01 secant tolerance, so the saved parameter check uses the exact forward conversion. The pinned writer emits both sides of adjacent faces, offsetting the second by twice model tolerance (2e-6 m here); it does not deduplicate all paired faces despite its docstring wording. The exact executed behavior gives 20/20/40 exported polygons. This tiny numerical offset is not a physical slab thickness.

Actual runs/honeybee-scenes-v5 converts compact/slender/stacked into 2/2/4 rooms, 8/8/16 apertures and 476/532/672 m2 aperture area. Each has 14,000 sensors, or 42,000 across all three studies. Three tests pass with a separately generated synthetic native facade, exact grid/area checks, changed source, invalid optical/sensor and native-window mutation controls. Evidence: evidence/document-intake/honeybee-scene.json.

All outputs remain simulation_executed=false, solver_ready=false and design_accepted=false. Scene geometry uses simplified massing room planes, not verified clear air volumes, native wall reveal/frame detail, full room program or complete site shading. Roof/ceiling material treatment and paired floor faces need physical applicability review. Ground/weather/sky/annual occupancy and actual annual sDA/ASE/view-based DGP are absent; current Radiance application-control blocks are unchanged. The conversion is currently standalone and not a unified workflow simulation task. It establishes an executed upstream scene adapter, not a finished daylight design or assignment.


## Unified source-inherited scene tasks

Workflow kind honeybee_scene accepts id, kind, depends_on and basis, with optional requires_pass/description. It requires an earlier concept_facade producer and inherits the exact revised IFC, original geometry, layout and thickness basis. Replacement IFC/project/layout/runtime fields reject. Scene settings and cited source documents, worker/dependency pins and reused modules enter the workflow source inventory. The runtime is supplied only through --honeybee-python to the unified CLI or workflow execute command, not document content.

The public runner can now stage all three scene conversions in the same reviewed-brief workflow:

```powershell
.venv/Scripts/python scripts/run_public_massing.py --out runs/new-public-scenes --source-cache runs/public-brief-intake-v1/sources --apply-work-plan --honeybee-python tools/honeybee-scene-runtime/Scripts/python.exe
```

Actual runs/public-honeybee-workflow-v2 passes twelve scoped concept/facade/preview/scene tasks, retaining all fourteen reviewed engineering packages pending. All three scenes record the newly generated facade hashes and 14,000 sensors each. HBJSON, Radiance geometry/materials and .pts files are covered by workflow artifact hashes. Scene conversion pass means geometry/input conversion only; every scene retains simulation_executed=false and solver_ready=false. Missing explicit runtime leaves scene tasks pending with no scene output directories.

The explicit runtime executable is hashed in a separate runtime_inputs map, preserving the delivery layer's exact source-plan input-set check. Runtime changes are checked during execution and by workflow verify, alongside source and artifact checks. Source-plan equality was not relaxed to allow arbitrary untracked extras. Source revisions, native facade tampering and downstream integrity gates retain their existing behavior.

Nine tests pass: three actual Honeybee workflow tests, three scene tests and three unified CLI tests. They cover exact revised-model inheritance, original unmet packages, missing runtime, forbidden replacement/runtime settings, changed cited source and generated point-file mutation. The runtime hash-control case is also exercised separately. Evidence: evidence/document-intake/honeybee-workflow.json. This supersedes the earlier standalone-only integration limit; complete site/ground/detail/annual solving and accepted design remain pending.
