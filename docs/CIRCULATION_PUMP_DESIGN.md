# Sourced circulation pump screening

`python -m bsa.circulation_pump_design --project examples/hvac-circulation/project-65mm.json --catalogue examples/hvac-circulation/pump-catalogue.json --thermal-basis examples/hvac-circulation/thermal-duty.json --rule-basis examples/hvac-circulation/regulatory-bases-65mm.json --pack regulations/hk/hvac-water-2026.11.08/pack.json --sources runs/hk-regulation-sources --out runs/new-pump-screen`

The single-pump circulation adapter preserves a baseline, evaluates every supplied candidate and reruns the selected candidate. Only a pump curve and its source change; routes, fluid, demands, targets and rule bases stay fixed. Every trial performs fresh native hydraulics, thermal transport and scoped pipe rules. Source hashes, native failures, warnings and rejection reports remain available. Candidate curves are never extrapolated for acceptance. Exact input/source hashes are checked throughout.

The explicit objective is `lowest declared preference among passing candidates`, with candidate ID as the deterministic tie-breaker. Preference is supplied with catalogue provenance; it is not implicitly cost, efficiency or energy. Valid catalogues contain 1–100 uniquely identified candidates, sourced head curves and finite preference values. Unsupported/malformed catalogues fail preflight. The example is entirely synthetic and provides no manufacturer pump data.

If no supplied candidate passes all checks, selected is null and no selected output is produced, even if the retained baseline passes. A baseline is comparison evidence, not an extra unlisted candidate. A selected rerun must pass before release. Manufacturer applicability, speed, efficiency, motor sizing, NPSH, controls and full regulatory coverage remain pending.

Actual official-BEC-backed examples retain two outcomes: the 65 mm demonstration selects supported-example after rejecting insufficient head and truncated domain; applying the same catalogue to the low-loss finite-elbow loop yields no feasible candidate. Both outcomes are expected evidence, not product recommendations. The finite-elbow trial consumes its derived network as a fixed standalone scenario; this screening does not update or certify the upstream IFC pump/curve binding. An accepted design iteration must explicitly reconcile the selected template/model and rerun saved IFC checks.

Evidence: docs/evidence/circulation-pump-screen. No official PDFs are redistributed. This is currently a standalone iteration tool; integration with automatic IFC revision and workflow selection remains pending.
