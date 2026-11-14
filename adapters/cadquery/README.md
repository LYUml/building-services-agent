# Isolated CadQuery worker

Tested Windows Python3.12 runtime:CadQuery2.6.1 and cadquery-ocp7.8.1.1.post1.
`requirements.lock` records the exact installed environment. No runtime binaries
or environment are committed. CadQuery/OCP bindings are Apache-2.0; linked OCCT
has LGPL-2.1 with the OCCT exception. Notices are in THIRD_PARTY.md.

The worker is standalone local CAD generation, not a new MCP/workflow producer.
Use an isolated environment and expose this repository's src through PYTHONPATH.
Set BSA_PROJECT_ROOT explicitly for external coursework paths; input JSON cannot
choose a workspace. Example command from the repository:

```powershell
$env:PYTHONPATH=(Resolve-Path src).Path
$env:BSA_PROJECT_ROOT='C:/absolute/project'
./tools/cadquery-runtime/Scripts/python.exe -m bsa.cadquery_rect_round `
  C:/absolute/project/local-lofts.json --out C:/absolute/project/new-cad-output
```

Input has exactly `source` and a nonempty `cases` list. Each case has a unique
path-safe `id` and positive finite SI fields:`width_m`,`height_m`,`diameter_m`,
`section_offset_m`,`taper_length_m`,`start_length_m`,`end_length_m`. Declare the
actual source/assumption basis. No loss coefficient or equipment rating follows.

Output includes exact metre-coordinate BReps for wall/outer/inner solids,
millimetre-coordinate STEP and a hash-bound kernel review. STEP is actually
reimported for units/volume. The inner bore extends0.1mm beyond caps only for
Boolean construction. Walls use section-plane offsets, not constant surface-
normal sheet thickness. Product/gauge/fabrication/source interpretation and
pressure acceptance remain separate. IFC/native CAD verification is downstream;
the worker explicitly retains IFC_verified=false and design_accepted=false.

See docs/VAV_INLET_CONNECTIONS.md for actual20case project execution and the
separately verified native IFC/AutoCAD composition using these geometry outputs.
