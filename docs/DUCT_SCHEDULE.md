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

Workflow tasks may now inherit an earlier air_allocation via depends_on and an explicit rooted tree/terminal membership; omit prescribed section flows. Exact identities, unique coverage and producer hashes are enforced. This binds flow, not physical topology or automatic sizing. See AIR_ALLOCATION.md.


## Candidate sizing in the same workflow

A section can supply `candidates` (each `id`, `width_m`, `height_m`) and a nonempty
`candidate_basis` instead of width/height. The existing `duct_equivalent.select_sizes`
screens the explicit velocity, friction and aspect limits and ranks feasible sizes
by area, perimeter and ID. Every candidate and rejection remains in `results.json`.
No feasible candidate yields a failed section, `calculation: null`, absent selected
dimensions and blank CSV dimension/calculation cells; downstream gates remain blocked.
Supplied dimensions and candidates cannot be mixed on one section. Candidate grid
assumptions must not be labelled as manufacturer stock or spatially coordinated sizes.

This combines with inherited `air_allocation` tree flows. 52 focused tests pass.
Actual private 47-section execution screens 357 candidates each (16,779 retained
checks), selecting exactly the prior candidate dimensions whose schedule had been
reconciled with the reopened DWG. This numerical replay is not a new native CAD
write/reopen or new coordination review. Auto-regeneration, physical fittings,
insulation, vertical constraints, fan duty and complete engineering acceptance remain
pending. The broad scope string retains separate source/physical topology checks.

## Interpreting source criteria

Keep a recommended pressure-gradient band distinct from a mandatory minimum or
maximum. When a brief calls for limiting friction, record the chosen upper cap and
its source; do not reject a larger, lower-friction duct merely because it falls below
a recommendation unless the actual project imposes that minimum. Retain maximum
velocity and aspect-ratio preferences separately from regulation claims.

Source-chart density and roughness may establish the chart-comparison basis, but
they do not establish actual operating air properties or fabricated surface quality.
Viscosity, temperature and dimension-grid/manufacturer availability still need their
own assumptions/evidence. Actual private source-backed replay after retrieval of the
classroom chart and criteria retains identical results for all 47 sections; numerical
correspondence does not clear installed geometry, ADPI or full engineering acceptance.

When multiple course sources provide velocity guidance, preserve system/application
context. A generic velocity band must not automatically override an office-specific
low-pressure supply-main/branch table. If system classification or source precedence
is unknown, retain that decision as an assumption or unresolved item. Browser-readable
text is not a hash-pinned original document; record a failed download as such and do
not claim verification of graphical fitting-table rows from their heading alone.
