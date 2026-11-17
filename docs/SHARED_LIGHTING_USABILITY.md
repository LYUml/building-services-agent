# Shared lighting workflow usability

Actual fresh MCP execution on 2026-11-17 completed the existing
`examples/shared-lighting-plan.json` workflow: shared electrical/geometry/IFC
and Radiance calculations passed, then AutoCAD saved and reopened the native
DWG and plotted its schematic PDF. The final manual requirement remains pending.
This is a synthetic integration example, not a coursework redesign or a real
lighting installation. See [source/model contract](LIGHTING_BINDING.md).

## Host path repair

The local project MCP profile still pointed to a removed older Codex-bundled
Poppler executable. Radiance was installed but absent from the startup flags.
The existing `bsa.codex_setup --refresh` was used with the actual current
Poppler executable and `tools/radiance-6/bin`. A parsed before/after comparison
confirmed that only these two runtime settings changed; AutoCAD, EnergyPlus,
Graphviz, Python, environment, timeouts and other controls were preserved.
No global configuration, security policy or user application was changed.

The new connection used the saved profile and successfully rendered its recorded
PDF with `bsa_render_artifact_page`. The existing desktop chat was not restarted;
hot reload is not claimed. Bundled paths can change with application updates:
check actual path presence before reusing a saved profile and explicitly refresh
an obsolete path. Installing/configuring a path is separate from executing it.

## Actual results and review

The actual Radiance 6.0.2 run reports arithmetic point mean 282.418 lux,
minimum 170.078 lux and minimum/mean 0.602219. Maximum relative change between the
specified initial and verification calculations was 3.64355%, below the explicit
synthetic 15% tolerance. These are checks against supplied example targets, not
Hong Kong office criteria, a regulatory area average or proof of convergence.
Electrical watts were checked against IES metadata; watts did not set brightness.

Native reopened entities retain all three circle centres and radii, the three
fixture/circuit labels and metre units. The actual rendered PDF was inspected:
three complete separate symbols and labels, no clipping/overlap and generous
margins. It is a fit-to-page schematic, with no fixed construction-scale claim.

A separate source-bound review passes only R2, the native conversion/reopening
and schematic visual obligation. R1 and R3 remain pending for their broader review.
All original workflow files remain unchanged. The producer's original pending
visual flags are preserved; the separate audit carries the scoped observation.
The audit stays `needs_review`, `design_accepted: false`. Native startup CER
diagnostic files remain retained alongside conversion/reopening/plot logs;
native acceptance here rests on saved/reopened entity and actual PDF evidence.

Actual sources, native outputs, rendered image and review remain in ignored
local runs. The [compact public receipt](evidence/shared-lighting-usability.json)
pins their bytes and records the configuration comparison and numerical results.
This reused the existing verified adapters and installed engines. No numerical
engine, dependency or new test suite was added for this host repair.

Manufacturer photometry, emitting origins, actual room/obstruction fidelity,
sampling coverage, glare, daylight, emergency lighting, protection and full code
acceptance remain separate engineering work. BSE3227 is unchanged awaiting
user feedback; full agent work remains active.
