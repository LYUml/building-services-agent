# Spatial terminal catalogue performance

`spatial_terminal_performance` inherits a passing `spatial_air_allocation` task.
It requires a basis mapping every terminal ID to exactly `settings`, `source`
and `classification`. Settings use the existing terminal_performance contract:
relative original source and catalogue paths, both hashes, and explicit conditions.
Catalogue metadata requires model, locator and explicit damper state.

Reuse decision: existing terminal_performance.calculate plus pinned fluids1.3.1
(BSD-3-Clause; existing attribution/license retained). No new engine or dependency.
The thin consumer supplies exact inherited maximum/minimum flows, returns bounded
T0.25, static and total pressure, and retains qualified NC source references.
NC is never interpolated. Outside flows return null performance and structured
requests to review sourced products or terminal allocation; no clamping.

The public workflow builder accepts `--performance-settings` only together with
`--air-balance --terminal-allocation`. It copies only declared source, catalogue
and settings files. No characteristic length, ADPI or installed selection is
inferred. Source/method pins and full report replay detect changed results.

Actual synthetic three-room native/MOOSAS runs have identical calculations.
Both produce two out-of-range maximum-flow cases with the archival source-bound
Krueger table, keeping the performance and final review pending. Official HK
lighting source bytes were supplied from the existing pinned cache. Aggregate
record: evidence/spatial-terminal-performance.json. These are integration trials,
not actual coursework, current product procurement or engineering acceptance.

Product applicability, room sensible loads, characteristic length, ADPI,
installation, room acoustics and complete fan duty remain unverified.

Validation:25 related tests pass with BSA_TEST_MOOSAS_TRANSFORM=1,including
source replay tampering,range pending,missing selections,forbidden flow
overrides and disabled-provider gates. Existing upstream IfcOpenShell reports
a ResourceWarning about its EXPRESS rule source handle;execution still passes.
