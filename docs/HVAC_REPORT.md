# Workflow-bound HVAC numerical report

Run `python -m bsa.hvac_report runs/study --out runs/new-report` after execution.
The report directory must be separate from the immutable run. The adapter verifies
all run source/runtime/artifact hashes before and after report preparation. It
requires one passing air_allocation, terminal_throw and duct_schedule task, and
rejects ambiguous/missing studies. It does not choose among multiple systems.

The editable HTML retains classified load inputs, geometry basis, maximum/minimum
lookup including explicit input L, leaf-group flows, selected duct sections and every
original requirement's execution/acceptance state. Cross-checks compare terminal
identities/demands and section flows with the allocation/tree. Source text is escaped.
Input L remains an assumption requiring applicability review; no ADPI verdict is
inferred. Failed numerical studies are not formatted as successful designs.

57 focused tests pass, including actual synthetic workflow export, changed artifact
rejection, inconsistent flow rejection and escaped source text. Actual private replay
produces 320 direction rows, 20 groups, 47 sections and all 34 source requirement
records. The fresh native plot is identical to the previously inspected image.

This is a single-system numerical HTML report, not a final coursework narrative or
an automatically reviewed PDF. Final references, geometry/flexible-route discussion,
visual report layout, source/ADPI/regulatory applicability and full delivery remain
separate requirements. The existing privately reviewed PDF remains a distinct artifact
until the general report renderer is integrated and reviewed.
