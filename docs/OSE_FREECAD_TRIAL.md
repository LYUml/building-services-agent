# OSE Piping / FreeCAD compatibility trial

## Observed result

**Blocked before geometry execution.** Official portable FreeCAD 1.1.4 was downloaded and its archive SHA-256 matched the release API value. Importing `Part` with the bundled Python failed because Windows Application Control blocked `lib/Part.pyd`. Code Integrity event 3077 independently confirms the signing-policy rejection (3033 and 3089 also recorded). No application-control policy was changed, no bypass attempted, and no live user CAD document was accessed.

Exact asset URL, archive/module hashes, OSE source hashes and failure evidence are in `evidence/ose-freecad/runtime.json`. The archive/runtime and unmodified source checkout are local ignored tools, not committed binaries. This is evidence against claiming a working integration on this host. The broader agent work can continue through its other verified engines.

## Source inspection and intended trial

OSE Piping by Ruslan Krenzler, pinned to `690ab65511be2cdbe8ce292cb59e5335d157ac09`, provides `OsePiping.Tee.Tee(document)`, explicit dimensional quantities and `create(False)` retaining editable Boolean features. That API can be used without the Dodo branch. We do not copy its geometry implementation.

The inspected implementation creates **socket fittings**. `H/H1/H2` locate outer ends, while `G/G1/G2` locate internal pipe shoulders. A connected pipe enters the socket; simply attaching pipe ends at the outer tee faces leaves an incorrect hydraulic/physical interface. The code also includes inferred wall-transition geometry, explicitly not standardized manufacturer dimensions. Product data, connection semantics and loss coefficients cannot be inferred from this library's existence.

`scripts/probe_ose_tee.py` is a prepared, syntax-checked **unexecuted geometry trial**, not a production adapter. It requires an unchanged pinned checkout and explicitly synthetic dimensions. When an approved FreeCAD runtime is available, run its Python with:

```powershell
& <approved-FreeCAD-Python> scripts/probe_ose_tee.py tools/ose-piping examples/ose-tee/dimensions.json runs/ose-tee-trial
```

The intended checks reopen FCStd and BREP, test a valid single solid and volume preservation, probe the three connected bores, test three shoulder-inserted annular pipes for material overlap, and require a deliberately displaced pipe to produce overlap. STEP is exported but is not independently verified by this script. The dimensions are software-test assumptions, not product ratings or project inputs. No trial report or generated geometry is claimed until the actual run completes successfully.

Even a future passing trial will leave IFC port/placement binding, branch hydraulics, saved IFC clash inspection, product suitability, drawing acceptance and regulations unresolved. Do not replace existing node geometry with these trial artifacts automatically.

## License boundary

Upstream LICENSE contains LGPLv3 while README says GPLv3. Tee.py and Piping.py have author/date headers but do not resolve that inconsistency. Preserve the upstream checkout and notices; do not describe it as MIT or silently vendor/relicense its code. This milestone retains original adapter/trial code and source references only. FreeCAD's bundled notices remain in the portable installation. Redistribution of either package requires its actual component-license review.
