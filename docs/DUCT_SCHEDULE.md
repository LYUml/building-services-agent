# Equivalent-round section schedule

`python -m bsa.duct_schedule project.json --out runs/new-schedule` recomputes
supplied rectangular sections with the existing fluids-backed equivalent-round
adapter. It writes `results.json` and `schedule.csv`; it does not select sizes,
solve network topology, or compute fitting losses and fan duty.

The project requires a nonempty `basis` description, `air` containing
`density_kg_m3`, `viscosity_Pa_s`, `roughness_m`, and a nonempty `sections` list.
Each section supplies a unique `id`, `flow_m3_s`, `width_m`, `height_m`, and
`limits` containing `actual_velocity_m_s`, `friction_Pa_m`, `aspect_ratio`.
Limits are declared project inputs, not automatically regulatory requirements.
The input JSON hash and basis accompany the result; original evidence and
applicability require separate review.

Exit 0 means supplied section checks pass; exit 2 retains exceeded criteria
and their computed values. Invalid input creates no output directory. Existing
outputs cannot be overwritten. `design_accepted` remains false in all cases.

Seven batch/physics tests cover independent numerical checks, CSV unit
conversion, source hash, output protection, failed limits and invalid batches.
Actual private execution recomputed 47 sections against explicit trial limits.
No coursework or vendor data is redistributed. Unified workflow registration,
network/geometry binding and complete engineering acceptance remain pending.

## Unified execution

Workflow kind `duct_schedule` takes `project` and optional `requires_pass`.
The executor records the project, batch adapter and equivalent-round module
as inputs. Exceeded criteria fail the task and block dependent tasks; passing
section checks do not accept the full sizing or design requirement. Source
changes invalidate saved run integrity.

Actual private execution runs both terminal lookup and 47-section schedule
from one plan, retaining eight pending work packages and all original passages.
The combined 26-test terminal, duct and workflow suite passes, including
failure dependency and changed-input controls. Network/geometry binding and
complete assignment generation remain separate work.
