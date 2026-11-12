# Separate tool source from project data

Common workflow module request discovery,and the MOOSAS surface/direct-IFC
recognition worker/providers now support the explicit host workspace. Upstream
checkout/dependency locations remain repository-local trusted runtime arguments.
The worker pins workspace.py;source/output separation and unselected-sibling
guards remain. Twenty-three related tests pass. A separate actual temporary
external-project trial with pinned official BEC source bytes verifies recognition,
selected LPD checks,disabled gates and rejection after removing host selection.
Its temporary files were removed after checks;only aggregate evidence remains in
evidence/external-moosas-recognition-workflow.json. No coursework was used in that
trial,and other adapters' remaining repository-only restrictions still apply.

General agent source,skills and software tests live in this repository.
Actual coursework inputs,runs and deliverables live in the user-selected
project directory. Existing historical repository runs remain preserved.

For the supported intake/common-module/BSE3227 calculation path,set an explicit
host workspace before invoking the installed agent from the project directory:

```powershell
$env:BSA_PROJECT_ROOT = 'C:/Projects/MyCoursework'
& 'C:/Tools/building-services-agent/.venv/Scripts/python.exe' -m bsa.project_start ./brief.pdf --out ./agent-work/project
```

The host root must be an existing absolute directory,not a volume root.
Documents cannot set this environment option. Source code and method pins remain
in the tool repository;project data pins may also point inside the selected
workspace. Unselected external siblings reject in the common module runner.
Verification of external module results requires the same explicit host root.
Unconfigured operation retains the earlier repository-local default.

This currently supports project_start,workflow_draft,work_plan_review,the common
module runner and requirements bindings used by the existing BSE3227 calculation
workflow. Other domain adapters with their own repository-only guards have not
all been migrated;do not claim universal external-workspace support or silently
fall back to generating private coursework inside the tool repository.

The actual coursework project was copied into its own directory with32source
files hash-checked. Original coursework files and historical tool-repository
runs remain unchanged. New requirements inventory and engineering workflow
execute with the coursework directory as cwd and output location. Four stages
pass;remaining engineering/native tasks are pending. Independent Decimal audit
also checks80terminal minimum flows against the supplied40%factor. This accepts
only the conditional arithmetic,not room loads,geometry,throw,ADPI or installation.
Private project sources/results remain outside commits to this tool repository.
See evidence/project-workspace.json.

Saved-native duct_schedule_check and duct_junction_review now also accept explicitly selected host project workspaces;their equation/geometry engines remain unchanged. Existing output-separation and source checks remain. See DUCT_SCHEDULE_CHECK.md.

The repeatable `hvac_project` configuration wrapper also accepts this explicit
workspace for configuration, sources and output. Its complete method inventory
continues to pin installed tool source. Twelve wrapper/workspace tests pass,
including absent host selection, unselected sibling paths and mutated inputs.
An actual private coursework configuration was created and loaded with328pins;
this trial did not execute the HVAC package or establish design acceptance.
