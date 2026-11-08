# Circulation thermal transport targets

Run a fresh native circulation solution and compare each named pipe's signed flow with a sourced constant-property transport target:

`python -m bsa.circulation_duty examples/hvac-circulation/project.json examples/hvac-circulation/thermal-duty.json --out runs/thermal-duty-new`

Required volume flow is thermal power / (density × specific heat × design temperature difference). Power uses explicit `kW_thermal`, not electricity or kVA. Density, specific heat and temperature difference each require units and source references. The fluid applicability source must explain compatibility with the hydraulic model's relative viscosity and specific gravity at the intended conditions; source references do not authenticate that engineering judgment automatically. No fluid-property defaults are inserted.

Targets name unique non-reference pipes and explicitly declare forward or reverse flow. Opposite flow cannot satisfy a target through an absolute-value conversion. Multiple pipe targets are independent local checks, not added loads: completeness, series-load accounting, diversity and simultaneous duties require separate project review. No flow tolerance is added to soften the thermal target. Native hydraulic failure remains an overall failure even when a thermal target passes. Native errors leave target flow unavailable and cannot pass.

The two synthetic basis files use identical hydraulics: 40 kW requires approximately 1.914 L/s and passes the approximately 3.037 L/s circulation; 100 kW requires approximately 4.785 L/s and fails. Both retain the passing hydraulic checks. These are mathematical demonstrations with approximate constant water properties, not equipment sizing or validated operating-temperature properties.

The output retains copied basis, input hashes, fresh native INP/RPT/BIN and a hash of the hydraulic report. The adapter does not yet bind actual heat exchangers, IFC, EnergyPlus loads or regulatory checks. It does not solve heat transfer, temperatures, thermal losses or controls and cannot establish full hydronic design acceptance.

## Source-linked workflow

Use task kind `circulation_duty` with `project` and `basis` paths relative to the workflow plan. It validates both inputs before execution, reruns native hydraulics and records both files in the workflow integrity inventory. Add `requires_pass: ["duty"]` to downstream tasks to block them when duty fails. A downstream `water_network` or another `circulation_duty` sharing that gate must consume identical hydraulic project bytes, including through transitive prerequisites. Other artifact correspondences are not inferred.

Example task: `{"id":"duty","kind":"circulation_duty","project":"project.json","basis":"thermal-duty.json"}`. This task executes its own fresh hydraulics; `depends_on` input inheritance is not supported. A passing task is a scoped thermal transport result and leaves design acceptance unresolved. Use the usual `bsa.workflow verify` command to detect changed basis, network or output evidence.
