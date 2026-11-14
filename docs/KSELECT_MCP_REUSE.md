# Existing K-Select MCP consumption

The user-owned [K-Select Agent Toolkit](https://github.com/LYUml/k-select-agent-toolkit)
0.1.1 at commit `3eecd3710e976927c4b7c639900e833d12150453` is consumed through
its existing MCP stdio server. No duplicate MCP, GUI backend or catalogue engine
is added. Its Apache-2.0 license and NOTICE identify the bundled CLI-Anything REPL
at `34f519533bc175d2fe287ab8316b0dd99bb9cc43`; manufacturer executables/databases
are separate proprietary software. No upstream source or native PDF is published
in this repository.

Actual initialize/get_capabilities/get_status/verify_result calls execute using
the toolkit's isolated installed runtime. The live session is blocked by an
existing report window; its guard is retained and no arbitrary dialog is closed.
Instead, the user's already saved 112CFM native result is verified against the
project's actual SD-01 minimum52.8831785L/s request, rounded by the toolkit to
112CFM (52.8581136L/s). All seven identity/flow/condition checks pass. The original
PDF hash matches its original saved result; a private copy is rendered and
actually inspected. This is reuse of an existing native run, not a new GUI run.

The adapter preserves raw NC10 and table dash but returns usable NC=null with a
warning. It also checks the summary's mislabelled throw against the feet table:
8ft converts to2.4384m, never8m. Those existing upstream guards are reused intact.

## Engineering findings

Native total pressure displays0.01inch water. Under an explicitly assumed
nearest0.01 display rule, its interval is1.24544455..3.73633365Pa. Existing archival
catalogue linear interpolation at the same effective flow gives3.98757238Pa,
independently checked with Decimal. The intervals do not match. The displayed
2.4908891Pa conversion is not a measurement with that precision. No pressure
method is silently replaced or new fitting correlation adopted.

At nominal8ft, all four inherited SD-01 diagnostic characteristic lengths meet
the existing paired20/40Btuh/ft2 manufacturer curve screen for the conditional
minimum-load scenario. With an assumed nearest-foot interval, north/south no
longer pass the whole-interval screen. Source-stroke margins and all internal
curve knots are retained. Maximum14ft stays outside paired40/60 source domains.
No actual load interpolation, accepted characteristic length or measured/native
ADPI result follows. The toolkit explicitly does not automate ADPI.

Course outputs: Diffuser Minimum Flow Review.html and
KSelect_Minimum_Flow_Check.json. Private MCP/PDF/source/method records are under
`07_Agent_Work/runs/kselect-mcp-existing-minimum`. The original rigid network
remains30conditional fitting paths/33numerical gaps; complete fan duty, acoustic
acceptance, installation and final delivery consistency are unresolved.
