# Integrated HVAC execution after upstream writer selection

The recent optional uc4n writer, source-plan verification and supporting-task
relations were exercised together through the existing hvac_project/hvac_package
entry, beyond the isolated sheet task. No new solver or runtime was introduced.
The exact MIT upstream/dependency pins remain in AUTOCAD_SCHEDULE_PROVIDER.md.

## Repeatable host sequence

Keep the original plan/configuration unchanged. Inspect the source before making
a fresh sibling plan: retain all requirements, quotes, tasks and ordinary gaps;
select writer=uc4n explicitly and declare only genuinely related supporting tasks.
Produce a verified bsa.source-requirements inventory for that exact plan, then
create a fresh hvac_project configuration with the original reviewed terminal and
ADPI settings and declared native/junction/path selectors. A previous plan's
requirements inventory cannot be reused for a changed plan.

```powershell
$env:BSA_PROJECT_ROOT='C:/ABSOLUTE/COURSEWORK'
python -m bsa.hvac_project create C:/ABSOLUTE/COURSEWORK/plan.json --out C:/ABSOLUTE/COURSEWORK/configuration.json --requirements-result C:/ABSOLUTE/COURSEWORK/inventory/result.json --terminal-review C:/ABSOLUTE/COURSEWORK/terminal-review.json --adpi-settings C:/ABSOLUTE/COURSEWORK/adpi-settings.json --junction-review-native-task native-sheet --system-paths-native-task native-sheet
python -m bsa.hvac_project run C:/ABSOLUTE/COURSEWORK/configuration.json --out C:/ABSOLUTE/COURSEWORK/fresh-package --font C:/Windows/Fonts/arial.ttf --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
```

Use actual project paths/task names and already-reviewed settings, not placeholder
engineering inputs. The host selects font/executable explicitly. Configuration
source/method pins must be current. Inspect package.json stage_errors and stages,
project-run.json, source-bound workflow verification and every required output.
The command returns 2 for review_required; an exit code alone cannot establish
which stages executed or a complete design. Preserve failed/incomplete records.

## Actual BSE3227 result

The full package executes without stage errors. Fresh native AutoCAD reopening
reconciles 718 generated entities. The existing whole-tree analysis covers 47
source sections, 48 nodes and 20 original outlet paths, retaining flow conservation
and complete source-path coverage. It reports nominal untrimmed CAD-centreline
friction only: physical straight lengths, fitting/terminal/equipment losses,
complete pressure and fan critical path remain unresolved. Parallel outlet paths
are not added and no fan duty is inferred.

Junction, terminal and ADPI reviews execute, followed by report HTML/PDF. The
24-page PDF retains 33 requirements, 388 checked numeric rows and 16 ADPI review
paragraphs. All 24 rendered report pages and the A1 drawing were actually
inspected; no observed table clipping/overlap or footer collision. Both PDFs'
decompressed page content matches existing public deliverables, so public report,
DWG and plot files are preserved rather than replaced for metadata alone.

All 33 requirements and six unresolved inputs remain. New workflow evidence links
related calculations on five broad requirements without accepting them. The
package result remains review_required and design_accepted=false. Source/module,
method, font, native producer, package and 49 artifact hashes were checked after
execution. These are scoped consistency/native/visual results, not complete
statutory or engineering acceptance and not autonomous raw-brief interpretation.
See [aggregate evidence](evidence/integrated-hvac-replay.json). Private source,
configuration, raw run and page images remain in the selected coursework workspace.
