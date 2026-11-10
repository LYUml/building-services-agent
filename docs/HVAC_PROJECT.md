# Repeatable HVAC project settings

`bsa.hvac_project` saves the interpreted plan and chosen package reviews in a
source-pinned configuration. It calls the existing `hvac_package` unchanged:
allocation, catalogue lookup, sizing, native drawing, reviews and report
preparation continue to use their existing engines and evidence contracts.

Prepare a configuration once after reviewing the project inputs:

```powershell
.venv/Scripts/python -m bsa.hvac_project create runs/project/plan.json --out runs/project/project.json --terminal-review runs/project/review.json --junction-review-native-task native --system-paths-native-task native
```

Add `--adpi-settings` and `--plan-clearance` when those reviews are configured.
The settings are optional; omission is retained, not counted as a passed review.
Native selectors must name declared `duct_sheet_native` tasks. Terminal layers,
ADPI applicability and obstacle coverage retain the package's existing contracts
in HVAC_PACKAGE.md and the respective review guides.

Replay all saved selections with one command:

```powershell
.venv/Scripts/python -m bsa.hvac_project run runs/project/project.json --out runs/project-package --font C:/Windows/Fonts/arial.ttf --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
```

Each output must be new. Plan, discovered source inputs, settings, referenced
ADPI document and configuration stay inside this repository. Relative paths may
refer to siblings within the repository; resolved paths outside it reject.
The configuration pins the complete discovered input inventory. Changed or
omitted inputs reject before package execution; changes during execution prevent
the `project-run.json` completion receipt. Review an intentional source change
and create a new configuration without overwriting the original.

Only the fixed `files`, `selectors`, `input_hashes` and schema fields are accepted.
Executable, shell-command and runtime fields are forbidden. Fonts and installed
AutoCAD are explicit host CLI arguments, never programs selected by document
content. This source inventory does not bundle the files or prove semantic
completeness; source files and installed dependencies must still be available.

The new receipt binds configuration/input hashes to `package.json` and records
the wrapper method. The package's own artifact manifest covers its workflow,
reviews and report; the separate receipt is not recursively added to that
manifest. Inspect both records. Package stage errors and unresolved tasks remain
in `package.json`; an incomplete result is not promoted to success by the wrapper.
CLI exit2 retains full acceptance pending, including a fully prepared package.

This is one command for an already interpreted project. It does not read a raw
brief into a complete design, supply unknown loads/products/installations,
certify Hong Kong compliance or submit coursework. Actual native reopening,
visual review and every original requirement remain necessary.

## Executed evidence

Eight targeted project/package controls pass,including source and setting
mutation,omitted inventory,rejected runtime fields,invalid selectors,output
protection and receipt suppression on mid-run changes. Mocked package controls
verify handoff only;they are not native evidence.

Separately,the private source-backed project replayed all seven actual stages
with no stage errors. It generated a fresh native DWG with independent AutoCAD
reopening/plotting and a22-page report with388 numerical rows checked. Source,
configuration,workflow,package and path-method hashes verify. Every report page
and the native plot are pixel-identical to hash-bound reviewed baseline renders;
the new first page and plot were also inspected. All34 requirement records and
nine unresolved tasks remain. See evidence/hvac-project-configuration.json.
Private configuration,source files and dense results remain outside Git.
