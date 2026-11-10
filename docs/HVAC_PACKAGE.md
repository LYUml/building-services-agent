# HVAC drawing and report package

Optional `--plan-clearance settings.json` adds a saved-native nominal-width obstacle
review through the same package invocation. Read DUCT_PLAN_CLEARANCE.md for exact
settings and coverage declarations. The stage inherits the selected native sheet
and original sizing/binding; replacement inputs are rejected. Its JSON and package
index retain tested planar-target results and missing obstacle coverage, without
establishing physical/three-dimensional or full design acceptance. Source pins are
checked before/after packaging; errors stay visible as stage errors.

Run a reviewed, source-linked HVAC plan through the existing workflow, dependency diagnosis, pending delivery review, numerical HTML report and PDF renderer in one invocation:

```powershell
.venv/Scripts/python -m pip install -e '.[reports,network,gis]'
.venv/Scripts/python -m bsa.hvac_package runs/project/plan.json --out runs/project-package --font C:/Windows/Fonts/arial.ttf --autocad 'C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe'
```

The output must be a new directory separate from all inputs. Supply an installed TrueType font explicitly; it is not redistributed. AutoCAD is optional at invocation, but required native tasks remain pending without it. See DUCT_SHEET.md and HVAC_REPORT.md for the underlying contracts. A raw assignment document must first undergo requirements intake and engineering interpretation; this command does not invent a plan from prose.

Open `index.html` for links to the native drawing, plotted sheet, report, workflow evidence, diagnosis and pending delivery review. `package.json` records stage errors, unresolved execution tasks and artifact hashes. A failed numerical producer prevents report preparation; PDF export failures retain the readable report and explicit error. The wrapper rechecks workflow integrity after reporting. Full source, engineering, visual and requirement acceptance remain separate, and `design_accepted` is always false. CLI exit 2 deliberately indicates that acceptance remains outstanding, including when all preparation stages succeed.

## Executed evidence

On 2026-11-10 the private coursework plan executed allocation for 80 terminals, catalogue lookup, sizing of 47 duct sections, a bound single-line sheet update, and fresh AutoCAD save/reopen/A1 plotting. The package contains a 22-page report with 387 complete numerical rows checked after PDF extraction and 34 requirement records. All artifact hashes and workflow integrity passed. Rendered report pages and the drawing were pixel-identical to the previously inspected renders. Nine execution tasks remain unresolved; this is a prepared design study, not a submission-ready or approved engineering design. Private files are excluded from Git.

The integration test executes a synthetic plan through the same wrapper, checks the report and pending review, rejects reuse of an output directory, and verifies that an invalid allocation is retained as failed without producing a misleading PDF report. Existing pinned engines and reporting components are reused; no additional solver or dependency is introduced.

## Saved terminal connection review

Add `--terminal-review <settings.json>` to automatically inspect the fresh native drawing after execution. Settings contain exactly `native_task` (the declared native sheet task ID) and `layers`, with distinct nonempty `supply`, `vav`, `terminal` and `flex` layer names. The package pins the settings bytes and inherits all geometry/calculation sources through the verified task ancestry (AIR_TERMINAL_DRAWING.md). No source replacements are accepted.

The review appears in terminal-review.json and the package index. Missing/failed native ancestry or geometric mismatch is retained in stage_errors and makes package status incomplete. Numerical reports may still be generated as design-study evidence; they do not clear a failed review. Omitting the option means this specific review was not requested, recorded as null configuration, not passed. Full acceptance always remains separate.

Actual private package replay checks 80 terminals and retains nine unresolved engineering tasks. Its 22 PDF report pages and drawing match inspected renders. A second run without AutoCAD retains the missing-native review error and incomplete package status. Six focused report/package/geometry tests pass. No new dependency or solver was introduced.

## ADPI scope review

Add `--adpi-settings <settings.json>` using the source-pinned schema in
ADPI_BASIS.md. The package inherits its new terminal lookup and includes
adpi-review.json plus an index summary of applicability and missing facts. Settings
and original source hashes are retained and rechecked. Pending/inapplicable review
is preserved as such; preparation success cannot establish ADPI acceptance. Omission
is recorded as an empty ADPI configuration, not a passed check. Review execution
errors remain stage_errors and make package status incomplete.

Actual private course-source-backed replay passes native drawing and terminal
connection preparation, retains pending applicability across 640 cases and produces
a 22-page report. Changed pages 1/16/17 were inspected; the rest and the native plot
match previously inspected renders. Eleven focused report/ADPI/summary tests pass.
