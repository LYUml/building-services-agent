# Project-scoped Codex startup

The existing BSA stdio MCP server now has a reusable local startup installer:

```
python -m bsa.codex_setup --autocad AUTOCAD_CORE_CONSOLE --pdftoppm PDFTOPPM
python scripts/probe_codex_setup.py --out FRESH_DIAGNOSTIC_DIRECTORY
```

For coursework, set explicit host BSA_PROJECT_ROOT to the selected existing
project before installing/probing. Without it the installer targets this agent
repository and binds data access to its existing ignored runs directory. Each
workspace gets its own .codex/config.toml building_services entry. The engineering
Python, source working directory and optional existing AutoCAD/Poppler paths are
absolute host startup settings. Defaults are120-second startup/1200-second tool
timeout, accommodating actual long source/native replay. No runtime/root comes
from assignment documents or tool arguments.

Official OpenAI documentation supports project-scoped stdio config and these
startup fields: https://learn.chatgpt.com/docs/extend/mcp
The installed Codex CLI help and generated app-server schema were also checked.
The installer preserves unrelated config bytes, backs up an existing local
file before append, is idempotent for matching settings and rejects conflicting
BSA entries. It does not edit global configuration, trust, approval/policy or
model settings. Completed historical BSE3124 is explicitly rejected. Existing
project trust requirements are retained; the installer does not grant trust.
Local configs/backups and runtime diagnostics are excluded from public snapshots.

scripts/probe_codex_setup.py validates the effective config read by Codex and
uses its actual app-server protocol: ephemeral diagnostic thread, MCP inventory
and a read-only reference-catalogue tool call. It sends no model turn. Optional
--ledger PROJECT_RELATIVE_LEDGER_DIRECTORY also performs a bounded gap read via
Codex itself. Diagnostics are separate from full engineering verification; a
saved-byte read does not refresh the ledger's native/source ancestry. The probe
closes only its own temporary app-server process. It does not restart user apps.

Executed evidence: both development and BSE3227 configs are recognized by Codex.
Both actual Codex backends discover38 BSA tools and execute the reference call;
the coursework backend also returns45 numerical gaps from the existing real
ledger. Three installer tests pass with verified durable receipt, covering
preserved settings, backups/idempotency/conflicts, separate project roots,
read-only history, invalid TOML and missing runtime. In addition, this active
development conversation exposes38 native BSA tool methods, successfully reads
the committed reference catalogue, and rejects an outside-root pressure read.
The isolated probe's hot-reload flag remains false because that probe does not
observe the live desktop chat; separate live-chat evidence records that outcome.

This establishes local tool wiring, not readiness of every optional runtime or
arbitrary brief-to-design acceptance. Current installed profiles configure
Python/AutoCAD/Poppler only. Source assumptions, pressure/physical/regulatory
and full-project acceptance remain explicit. Workspace selection still matters:
use the coursework workspace for coursework and the agent workspace for general
development. The development profile cannot write to a coursework data root.

## Explicit runtime refresh

Install the optional codex-setup extra for tomlkit==0.15.1, then add --refresh to
the setup command when updating existing runtime locations. Fresh installation
still uses the standard-library renderer. Refresh reuses upstream TOML Kit
instead of implementing a TOML editor:
https://pypi.org/project/tomlkit/0.15.1/
MIT copyright/notice is retained in third_party/licenses/tomlkit-0.15.1.txt.

Refresh updates the known BSA module launcher's Python command, source cwd,
selected data-root binding and only the optional runtime flags explicitly
provided. Unspecified AutoCAD/Poppler and other launcher arguments remain.
User enabled state, timeouts, approval policies, other environment values and
unrelated settings remain unchanged. Unknown launchers and ambiguous flags being updated
reject before writing. An exact baseline TOML roundtrip is required, and parsed
post-update data must match only the intended changes. A library layout that
cannot be reproduced byte-for-byte is rejected rather than normalized silently.
This guards the upstream documented out-of-order array-table layout limitation.

Writes flush a same-directory temporary file before atomic replacement, with
observed concurrent-change checks. Existing config is backed up; differing
snapshots get content-derived backup names instead of overwriting old backups.
Failure controls preserve the original and remove the temporary file. These
are local recovery/correspondence controls, not authenticated or adversarial
filesystem transaction guarantees. No global trust, policy or model setting is
changed, and no user application is restarted.

Seven installer/refresh tests and the durable receipt verifier pass. Actual host
execution creates an isolated project profile, refreshes real AutoCAD/Poppler
arguments and verifies backup plus subsequent no-op. The actual Codex backend
still discovers38 tools and executes a read. Both existing development/course
config files remain byte-identical, and both actual backends pass read-only
rechecks; coursework returns45 existing ledger gaps. Configuration correctness
is separate from physical/model/engineering acceptance or a changed engine's
native verification. No new engineering loss value is introduced.

The final suite also rejects an ambiguous updated flag and a library
normalization result while preserving original bytes. Apply runtime refresh
between engineering operations and repeat engine-specific native acceptance
when an executable changes; tool discovery alone is not engine validation.
