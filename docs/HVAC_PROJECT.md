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
The configuration pins the complete discovered input inventory,including
supplemental ADPI fact-evidence documents. Changed or
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

## Optional terminal performance selection

`hvac_project create` also accepts `--terminal-performance <settings.json>`.
The file,original manufacturer document,performance table and adapter method
enter the complete input inventory. The saved configuration replays the optional
stage without another flag. Only one declared terminal lookup is supported;
ambiguous selection rejects instead of choosing arbitrarily. Existing configurations
without this optional file remain valid. See TERMINAL_PERFORMANCE.md.

The actual eight-stage replay has no stage errors and includes80 terminals/160
pressure operating cases. All23 report pages and the native plot match their
hash-bound reviewed baseline renders;388 numerical rows,34 original requirements
and14 ADPI paragraphs remain checked. Independent decimal arithmetic verifies
both pressure columns for all160 cases. Twenty-two targeted tests cover the
stage/configuration handoff and source-mutation controls. Full fan pressure,
room acoustics,ADPI and engineering acceptance remain pending. Evidence:
[terminal-performance-package.json](evidence/terminal-performance-package.json).
