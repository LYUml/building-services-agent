# Clean-checkout native MCP verification

A new checkout/environment at implementation 7632371 now repeats the six actual
stdio calls after the portability repairs, with the same constrained installation.
Independent inspection passes, native DWG reopening reconciles 718 entities, and
the 23-page report checks 388 numeric rows. The actual returned A1/report17 PNGs
were viewed. Pip check and the selected-profile doctor pass. This does not approve
the isolated scenario as coursework. See
[current native MCP evidence](evidence/current-candidate-native-mcp.json).
The a6236c3 evidence below remains historical and has not been relabelled.

The current native HVAC/MCP path was executed from a new GitHub clone at
`a6236c3b88dcb660263f1a55ac71cecf9ab35e90`, installed into a new Windows
CPython 3.12 environment with drawing, mcp, codex-setup, reports, network and
spatial extras. It does not reuse the development environment's site-packages.

A real SDK stdio session listed 40 tools and completed six calls: prepare an
explicit project configuration, run the complete HVAC package, independently
inspect it, retrieve two hash-bound PDF pages and read the committed reference
catalogue. The catalogue revision equals the new checkout's actual HEAD.
The package has no stage errors and independently passes integrity inspection.
AutoCAD saved/reopened the native drawing and reconciled 718 generated entities;
the 23-page report checked 388 numerical rows. Actual MCP-returned A1 and report
page 17 images were viewed; other report pages were not visually re-reviewed.
This uses the isolated actual-project scenario, not a changed coursework baseline.
Engineering status remains review_required and design_accepted=false.

All 346 product Python files match the working implementation after newline
normalization. Only 153 are byte-identical because Git checkout line-ending
conversion differs from the existing worktree. Old method receipts were not
rehashed; the new configuration pins the actual new checkout bytes.

## Repeat the selected installation

From the intended source checkout, in its dedicated environment:

```powershell
python -m pip install -c locks/hvac-mcp-windows-py312.txt -e ".[drawing,mcp,codex-setup,reports,network,spatial]"
python -m pip check
bsa doctor --extra drawing --extra mcp --extra codex-setup --extra reports --extra network --extra spatial
```

The constraint file pins 42 observed dependency versions for Windows/Python 3.12.
A second fresh environment installed using it and exactly matched all 44
distribution versions, including the source project and pip. Pip check and the
selected-profile doctor passed. Constraints do not install additional packages,
pin build isolation/bootstrap tools, bundle native engines, license AutoCAD or
prove behavior on other Python/platform combinations. Preserve explicit host
AutoCAD/font/Poppler configuration and BSA_PROJECT_ROOT; see CODEX_LOCAL_SETUP.md.
No existing user configuration or application was restarted.

[Aggregate evidence](evidence/clean-checkout-native-mcp.json) records the executed
scope. Private project inputs, paths and full runtime records are not published.
Full-regression CI is still running at this checkpoint; this is not a final
release or user acceptance statement.
