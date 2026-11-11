# Conditional electrical analysis module

`bsa.single-phase-circuits` exposes the existing engine.calculate/cli.run through
`analysis.electrical.single-phase-circuits` and `bsa.electrical-circuits/1`.
No electrical solver or physical model is rewritten. The existing ezdxf1.4.5
dependency remains pinned;adapter licence metadata is NOASSERTION because the
repository's own distribution licence remains undecided.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/modular-electrical-plan.json --out runs/electrical-module
```

The source request has exactly one project role with its hash. Electrical kW,
VA,A,V and metre quantities remain explicitly distinct. Circuit/device IDs,
source references,current,corrected ampacity and voltage-drop results retain the
existing conditional calculation semantics. Phase VA buckets are arithmetic
labels,not a three-phase load-flow/phasor/neutral-current calculation. Unresolved
fault disconnection,breaking capacity,coordination,lighting,source and drawing
checks remain in the payload/report. geometry_bound is always false.

The existing adapter also writes DXF,SVG and HTML artifacts. These are schematic
outputs;no native DWG reopening or physical route/installation acceptance is
inferred. Existing ASCII drawing-label restrictions remain. Module verification
recalculates from the exact source and compares
both retained numerical report and common payload. Updated artifact hashes do
not clear altered calculation values. This is source replay,not independent
mathematical corroboration or authenticated execution.

Completed execution can carry failed numerical checks. Workflow module_analysis
uses that payload status;failed/disabled results block required consumers. Host
disable returns unavailable without payload. Jurisdiction selection and native
model binding are not implemented at this boundary;they remain separate work.

Twenty-three related tests pass. Actual public1circuit and independent2circuit
projects complete and verify. Public positive,deliberate low-breaker failure and
disabled scenarios retain correct dependency gates and delivery correspondence.
Independent Decimal arithmetic checks the first scenario's seven circuit values.
Complete electrical/MEP acceptance and the full regression remain unfinished.
