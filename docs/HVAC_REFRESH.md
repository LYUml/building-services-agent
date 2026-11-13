# Replaying a project after a tool upgrade

Normal project loading now points to this existing read-only diagnosis when
pinned files change or disappear. The error distinguishes tool-only drift from
changed/missing project inputs, lists at most five affected paths and provides
the full inspect command. Missing inputs reject before engine execution instead
of leaking an unhandled missing-file error. No configuration is refreshed
implicitly. Fourteen project tests pass; a real stale coursework configuration
reports eleven changed and thirty added tool files, zero changed project inputs,
and remains byte-identical. See evidence/hvac-stale-guidance.json. This is a
diagnostic check, not a new engineering replay or transferred acceptance.

`hvac_project.load` deliberately rejects stale source/method hashes. The new
`hvac_refresh` adapter diagnoses drift and prepares a fresh configuration when
the original project inputs remain unchanged. It preserves the old configuration,
old requirements inventory, original plan/quotes/gaps and existing reviews.

```
python -m bsa.hvac_refresh inspect OLD_CONFIGURATION
python -m bsa.hvac_refresh prepare OLD_CONFIGURATION --target NEW_CONFIGURATION --out NEW_REFRESH_DIRECTORY
python -m bsa.hvac_refresh verify NEW_REFRESH_DIRECTORY
python -m bsa.hvac_project run NEW_CONFIGURATION --out NEW_PACKAGE --font HOST_FONT --autocad HOST_AUTOCAD
```

For project data outside the installed tool repository, select the same explicit
host `BSA_PROJECT_ROOT` for every preparation, verification and execution command.
An unselected external sibling rejects. Documents cannot configure that root or
select an executable. Engine/font paths remain explicit host runtime arguments.

Drift classification uses the reserved tool method folders: `src/bsa/*.py`,
`scripts/*.py` and `contracts/*.json`, including descendants. Project data belong
in the separate selected project workspace, not in these method directories.
Changed, removed and newly added method files are listed. Every original pinned
non-method file, including the prior requirements result, must still match its
recorded hash. Changed/missing project inputs reject before writing a new output.
This preparation is not a way to acknowledge changed drawings, catalogues,
criteria or assignment documents without source review.

The adapter reuses `hvac_project` inventory/create/load, the common requirements
provider and existing project/workspace validation. It creates a new request and
requirements inventory for the exact original plan, then creates a separate new
configuration with the same settings and review selectors. Requirements failure
does not create a configuration. Original requirements-run directories cannot
contain new outputs. Source and method changes during preparation remain failure;
the original stale hashes are never rewritten to accept the upgrade.

`verify` independently reconstructs drift, validates all old non-method/current
method snapshots, fresh requirement artifacts and exact new configuration inputs.
Preparation/verification does not invoke engineering or transfer review acceptance.
The fresh configuration must execute through ordinary calculation, native CAD,
plot, source and visual checks. Unsupported or changed engine semantics remain
execution/review work rather than being certified by a source hash.

## Actual project replay

An authorized private BSE3227 project exposed seventeen changed tool methods and
thirty-four added methods, with no original project-file change. The fresh
requirements inventory retained all 33 requirements and six unresolved inputs.
The new configuration executed the full existing HVAC package in that project
workspace: six postprocessing/report stages completed without stage errors;
five numerical/drawing tasks passed, including native DWG save/reopen. Its saved
drawing correspondence retained 80 terminals, 20 VAV groups and 47 rigid sections.

The actual 24-page report and one A1 drawing were rendered and inspected. Their
page content streams and extracted text exactly match the prior reviewed local
outputs. The declared 10 m print reference measures approximately 99.991 mm at
1:100. This checks the plotted reference, not independent original-building
scale. Original clean public-facing outputs are preserved; fresh configurations,
raw course sources, runs and detailed visual receipts remain in the private
project workspace and are not committed here.

ADPI remains unverified; source load-domain applicability, characteristic lengths,
scale/installation, physical connections and full engineering acceptance remain
unresolved. No input gap or manual acceptance was cleared by upgrading software.
This trial verifies repeatability of one existing interpreted project, not new
design interpretation or automatic completion of arbitrary assignments.

Forty-six related tests pass, covering tool-only drift, changed data, new methods,
command fields, source/target tampering, nested old-inventory writes, host workspace
selection, unavailable inventory, mid-preparation data changes, existing wrapper,
package and performance behavior. Aggregate private-
project evidence is in [hvac-refresh.json](evidence/hvac-refresh.json); course
documents, configurations and detailed results remain excluded. No new external
dependency or engineering engine is introduced; upstream attribution is unchanged.
