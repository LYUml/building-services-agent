# Related calculations beside the complete requirement

A broad source requirement can span load calculation, terminal selection, drawing
and physical/ADPI review. Mapping it only to its primary manual task previously
left already-executed calculations absent from that requirement's evidence panel.
A source requirement may now declare optional `supporting_tasks`:

```json
{"id":"R1","passage":"P001","quote":"Original complete source quote","task":"review","supporting_tasks":["allocation","terminal-lookup"],"acceptance":"Complete original obligation remains pending"}
```

Supporting tasks must be unique existing tasks, different from the primary task.
The existing primary task-to-requirement coverage rule remains. This relation is
for evidence discovery and does not create dependencies, change task execution,
or clear missing inputs. Use existing requires_pass for actual dependency gates.
No keyword matching chooses supports automatically; the host inspects the full
source and explicitly declares related existing tasks.

Workflow JSON adds supporting_evidence only when declared, with each task's actual
status, scope and original artifact paths. The existing local HTML links these
files beside the primary requirement. Failed/pending tasks retain those states;
diagnostic files are not approved designs. Primary execution and acceptance stay
unchanged. Source-plan verification and delivery context reconstruct these maps
and reject missing/forged support states, files or source bindings. The common
requirements-inventory contract preserves the declared relation and source hash.
Delivery review can cite these existing recorded artifacts through its existing
path/hash interface; the primary/manual review gates still apply.

This reuses existing workflow, requirements provider, report renderer and delivery
audit; no new numerical/CAD engine, dependency or external package is introduced.
It improves reuse of already-produced evidence rather than recalculating a new
physical design or claiming an unimplemented capability.

## Executed real project

A fresh BSE3227 sibling plan changes only supporting-task declarations on five
requirements. All original quotes, acceptance text, primary tasks, 33 requirements
and six ordinary input gaps remain. The original plan is unchanged. The common
requirements provider executes, full task graph reruns, independent workflow and
delivery-context checks pass, and a pending review template is produced.

The five load/minimum-flow/schedule requirements expose related allocation,
terminal, sizing and drawing files while retaining pending primary status. The
native task remains pending in this trial because AutoCAD was not requested;
previous native/visual evidence is not transferred. ADPI/physical applicability
and full project acceptance remain unresolved. Aggregate evidence is in
[evidence/supporting-requirement-evidence.json](evidence/supporting-requirement-evidence.json).
