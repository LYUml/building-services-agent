# Classified airflow allocation module

Provider `bsa.classified-air-allocation` exposes capability
`analysis.air.classified-allocation` through the existing module request/result
runner. It reuses air_allocation, air_load and service_areas unchanged, including
the installed Shapely2.2.0 nearest-centre geometry engine. No solver/dependency
is added. Existing upstream notices and licenses remain in THIRD_PARTY.md;
the wrapper does not assign an unselected repository distribution license.

The request has exactly one source role, `project`, pointing to the existing
allocation project JSON with its SHA256. That file supplies the boundary hash,
classified load inputs, explicit terminal centres, geometry basis, turndown and
optional source-document references. Discovered files must remain in the tool
repository or explicitly host-selected BSA_PROJECT_ROOT workspace.

```powershell
.venv/Scripts/python -m bsa.modules path/to/request.json --provider bsa.classified-air-allocation --out runs/new-allocation
```

Payload `bsa.air-allocation/1` carries stable terminal IDs, allocated load areas,
maximum/minimum L/s, thermal kW and turndown, with a hash-bound original analysis
artifact retaining all source classifications and assumptions. Common quantities
check unique IDs, flow conservation, turndown, frame and artifact paths. Delivery
verification reruns the existing allocation method from sources and compares the
entire stored result and common payload; changing hashes alone cannot accept a
rewritten result. This replay is correspondence verification, not independent
physical validation. The common frame is host-declared, not surveyed/georeferenced.

The actual private-project module completes over80terminals and matches its
prior native-workflow allocation exactly. See evidence/common-air-allocation.json.
Forty-one related allocation,wrapper,requirements,module-contract and electrical
rule tests pass. A separate water-rule class setup failed with a retained
application_control_block diagnostic;this is not included in the passing set.
Source mutation, rewritten artifact/payload, duplicate ID, unsafe path, invalid
frame, disabled-provider and unsupported-runtime controls execute in tests.
Automatic workflow dispatch through this provider remains unfinished.

Execution completion retains acceptance pending, geometry_bound false,
room_sensible_load_verified false and design_accepted false. This is a uniform
allowance/constant-property thermal balance and nearest-centre allocation, not
detailed room load simulation, air coverage, ADPI, pressure/fan design, installed
CAD/BIM validation or whole-project regulatory acceptance.
