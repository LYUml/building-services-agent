# Source-bound complete represented network analysis

`bsa.source_network_analysis` binds every saved port of the verified compound
network to original design flows, reads actual native cap sections and straight
extrusion lengths, and traces every inlet-to-outlet path.

```
python -m bsa.source_network_analysis run COMPOUND_NETWORK_RUN --out FRESH_RUN
python -m bsa.source_network_analysis verify FRESH_RUN
```

The host explicitly selects external coursework using BSA_PROJECT_ROOT. Output
must be fresh and outside the immutable producer. No replacement IFC, air
conditions, flows or lengths can be passed. Exit 2 preserves incomplete pressure
and full engineering scope even when flow/integrity checks pass.

## Reuse and source binding

The adapter reuses source_compound_network's complete source/native replay,
duct_chain_analysis.source_schedule and boundary_paths, native annular cap
extraction, and duct_equivalent's existing equivalent-round straight-friction
method. Pinned MIT fluids 1.3.1 supplies the original Colebrook/Darcy engine;
the [official documentation](https://fluids.readthedocs.io/fluids.friction.html)
was checked. No new flow, geometry or friction engine is introduced. This does
not extend the original equivalent-round method's applicability or substitute
hydraulic diameter, Fanning friction or a pressure-dependent airflow solution.

Original source sections bind retained straights, elbow incident ends, each tee
and cross core arm, both transition ends, and each compound boundary port through
actual stable native identities. Every actual saved port must be covered once.
The original air conditions are inherited from the passing native drawing →
sheet → selected schedule ancestry, without reclassifying assumptions as measured.

Starting with original outlet design demands, the adapter independently accumulates
flow through actual saved directed connections and one-inlet splitting/through
products. Every derived port flow must agree with its original source section.
Cycles, duplicate peers, missing bindings, unsupported flow directions and
source-flow changes reject. Product, linked-interface and outer-boundary balances
are all checked. The absorbed common section is separately reconciled from both
original junction sides inside the compound construction; removing its standalone
body cannot remove its original flow obligation.

## Native quantities and pressure-path limits

Native mesh material annuli supply clear dimensions at every port, including
elbows, variable transitions and the compound junction. Actual rectangular
design velocity and velocity pressure use those dimensions. These are calculated
design quantities, not measured site flow/velocity. Fitting core dimensions may
differ from nominal adjoining source sizes. Original source flow and independently
graph-derived flow are recorded separately.

Every supported straight uses actual saved hollow-profile extrusion length and
the unchanged source air conditions. Its known straight-friction contribution
does not include upstream/downstream fitting wall friction. The common existing
boundary-path tracer checks all ports/products and each physical terminal path.
A shared straight may appear in multiple outlet paths but remains one physical
body; parallel path losses must never be summed as system pressure drop.

Every fitting inlet-to-outlet route remains an explicit missing loss obligation:
applicable geometry/flow ratio, total-pressure coefficient, actual reference
port velocity, cited source/edition and whole-fitting wall-friction convention.
Joint, terminal and equipment losses/boundary pressures also remain unresolved.
No coefficient is assumed zero or copied from a mismatched round-pipe fitting.
Complete path pressure, critical full path and fan duty remain null/incomplete.
The across-product straight subtotal is not a fan/system pressure requirement.

Verification freshly reconstructs original source mappings, native cap and
straight quantities, graph-derived flow, all paths and missing obligations. It
does not accept a stored count or green flag in place of source/native replay.
All original requirements, source scale/elevation/gauge assumptions, physical
joint/clearance, products, installation and full engineering acceptance remain.

## Executed real network

The actual 102-body/101-interface network binds all 223 saved ports. Boundary
inflow and outflow are each approximately 12.0003727634 m³/s. All products and
interfaces conserve the original prescribed design flow. The shared absorbed
D-01 obligation also agrees from independently accumulated upstream/downstream
quantities, approximately 10.5797378269 m³/s.

All 45 retained native straights reconcile dimensions/flow to the source
schedule. All 20 terminal paths are traced separately. Their known straight-only
friction contributions range approximately 5.67066–31.85560 Pa; these values are
not complete path pressure, a full critical path or fan duty. Seventy-six distinct
fitting inlet-to-outlet loss paths across 57 native fitting bodies remain
unresolved. Original geometry changes and all 33 requirements remain explicit.

Eleven source/native/friction/path tests pass, including rejection of a stored
unknown loss relabelled zero or an incomplete budget relabelled complete.
The saved review HTML contains all
20 path rows and 45 straight rows with pending full pressure. Actual numerical
table inventory/values are checked; visual delivery and full engineering
acceptance are not established. The report title and filename have no internal
iteration labels. See [safe aggregate evidence](evidence/source-network-analysis.json).

The actual standalone verify CLI independently recomputes original source
ancestry, all native quantities, graph/source flows, pressure paths, missing
obligations and saved report content. Integrity passes with the pressure budget
and design acceptance still incomplete. Native/source/test evidence does not
establish full visual or professional project acceptance.
