# Workspace isolation and clean-source startup

The normal electrical CLI, workflow execution/intake and delivery-review writers
now require permitted input/output workspaces before producing files. The CLI
also rejects an unselected review path before executing any project task.
Development outputs use the repository `runs` tree. External project operations
require explicit host `BSA_PROJECT_ROOT`; a document cannot set it.

The completed `polyu_bse3124` context is excluded from engine workspaces, including
descendants and a selection of its parent directory. The known Desktop location
remains protected when the tool source is installed in another directory.
MCP's shared path boundary checks the same rule, including its direct JSON writer.
Historical context can still be read with ordinary read-only file tools; it is
not selected for generators or configuration. These checks do not change Windows
permissions or act as a sandbox for arbitrary Python programs.

Default startup no longer depends on an existing ignored `runs` directory.
The installer and an unconfigured default server initialize only their owned
development data directory. Missing external projects remain errors; protected
resolved data directories cannot be configured. The installer reports
`data_root_created` separately from whether configuration bytes changed.

## Executed verification

- New controls reject unselected electrical, intake, workflow and review outputs
  before creating them; a positive explicitly selected external project produces
  real calculations and editable DXF while preserving its source.
- Synthetic history fixtures test exact/descendant selection, broad parent
  selection and the actual MCP JSON writer. The real history path is queried
  only; no test files or generators are run there.
-32legacy test modules now put their internal scratch data in the permitted
  development tree. Existing external host-selection controls stay external.
  Across these modules,202tests complete:190pass and12skip. Skips do not prove
  optional-engine availability. No engineering formulas or source criteria changed.
- After adding delivery/bootstrap checks,67targeted tests pass; final focused
  history/setup/external-project checks run20tests successfully.
- An independent copy of the public source, initially without `runs`, `.codex`
  or an environment, installs into a new virtual environment. Source identity
  is checked rather than accidentally importing the original editable checkout.
  The installed setup initializes data, doctor/pip checks pass, and the actual
  installed CLI saves/reopens an AutoCAD drawing and retains both requirements
  with a separate pending review. Its PDF pixels match the inspected fixture.
- The fresh MCP process discovers40tools, independently inspects that native
  drawing and rejects a path outside its selected data root. All343current
  product Python files match the isolated source copy; final setup is idempotent.

See [executed receipt](evidence/workspace-isolation.json). This establishes
the listed entry-point behavior and a synthetic native workflow, not full agent,
physical engineering or statutory acceptance. BSE3227 remains unchanged awaiting
user review; the broader agent goal remains active.
