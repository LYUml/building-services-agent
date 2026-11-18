# Install the prerelease

Windows CPython 3.12 and Git are prerequisites. AutoCAD is separately licensed
and installed; this setup never installs native applications, changes system
PATH, grants project trust or changes global MCP settings.

Download the source ZIP from GitHub Releases and extract it into a writable
folder. Double-click **Setup.cmd** (or run it in a terminal to retain its output).
The launcher can reuse an existing Codex-managed Python 3.12. If Python is
missing, install CPython 3.12 and retry. Internet access is required for pinned
Python packages and Git source history. Keep the installed source folder in place.

```powershell
.\Setup.cmd
.\Setup.cmd --profile hvac --project-root "C:\Projects\My building" --autocad "C:\Program Files\Autodesk\AutoCAD 2027\accoreconsole.exe"
```

The default CAD profile includes drawing, MCP, project configuration, document
intake, modules and reports. HVAC adds the existing network and spatial extras.
Other optional solvers remain opt-in; see [capabilities](CANDIDATE_SUPPORT.md).
Only one detected AutoCAD installation is selected automatically. With multiple
installations, pass `--autocad` explicitly. No detected AutoCAD means native DWG
execution remains unavailable; a successful MCP setup does not claim otherwise.

Setup creates `.bsa/venv`, verifies pinned direct dependencies, runs the existing
MCP contract audit and a real stdio handshake plus read-only catalogue call.
It writes receipts in `.bsa`, then installs/refreshes only the known BSA entry in
the selected project's `.codex/config.toml`, preserving unrelated settings and
making backups. An unfamiliar launcher is rejected for manual reconciliation.
It also installs all 11 bundled skills into the selected project's
`.agents/skills`. Each receives the actual source/Python/project context so its
documentation and commands remain usable outside the source repository.
`.agents/bsa-skills.json` records managed hashes: unchanged managed skills can
be updated; edited or unrelated conflicting skills cause an early error before
dependency installation or configuration changes. Unrelated skills are retained.
In the source repository itself the original skills are used without rewriting.
Generated skills and their ownership file contain local paths; keep them local.
Open that project in Codex and review normal project trust; other MCP hosts can
reuse the saved command, args, cwd and environment. Host UI connection is a
separate check. Never select the completed BSE3124 workspace.

An extracted release restores its exact commit's Git objects for immutable
reference retrieval without checking out or overwriting source files. Existing
Git checkouts are reused. Rerunning setup reuses its isolated environment and
refreshes pinned dependencies; logs and historical engineering runs are retained.
No existing `.venv` is changed. To start over, extract into a fresh folder rather
than deleting user data. Do not move an installed Python virtual environment.

The ZIP is a complete source-layout distribution, not a standalone wheel or
bundled AutoCAD. Native save/reopen, visual plots and engineering applicability
still need project-specific review. Revit native authoring and whole-project
statutory certification are not release claims. Software prerelease publication
does not mean the user has accepted an engineering deliverable.
