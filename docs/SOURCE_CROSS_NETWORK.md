# Partial source cross network integration

`bsa.source_cross_network` adds only independently verified, actually authored
four-arm source candidates to a fresh source tee/elbow network.

```
python -m bsa.source_cross_network run SOURCE_CROSS_RUN --out FRESH_NETWORK_RUN
python -m bsa.source_cross_network verify FRESH_NETWORK_RUN
```

External project paths require explicit host `BSA_PROJECT_ROOT`. Output is fresh
and outside the source run. The original network is preserved. CLI exit 2 keeps
incomplete network/design scope explicit even when native/integrity checks pass.

## Reused methods

Source verification replays cross candidates, parent tee network, original tee
components, selected elbows and the native source drawing/calculation ancestry.
The adapter reuses `source_tee_network.compile_model` for directed two-end trims,
`bim`/`duct_elbow_backbone` for native trimmed rectangular bodies, and the existing
native representation/property/frame snapshots and saved IFC inspector. The
original tee trim properties survive separately from the new cross trim fields.
The inherited minimum remaining length is unchanged.

Pinned official IfcOpenShell `project.append_asset` imports the verified existing
components with restored world frames/owned port placements. Actual tee and cross
interfaces are rebuilt from their distinct stable source identities. Cross
interfaces additionally require matching SOURCE/SINK roles, coincident opposing
cap planes and rectangular section roll. No connection is invented at a blocked
node. No new geometry engine or dependency is introduced.

The saved combined model must preserve complete source body representation and
property fingerprints, world frames, port identities/directions, exact native
connections, reference-storey containment and one supply system. Native schema/
EXPRESS inspection executes. Independent verification reconstructs the source
trim model and expected component/link inventory rather than trusting the output
JSON counts. Remaining blocked nodes and original requirement IDs remain explicit.

Full raw clash and clearance checks must run separately on this new model with
the source policy. Topology/schema success cannot clear coordination, physical
product joints, fitting losses, pressure, installation, architecture/equipment
coverage or complete regulatory/design acceptance.

## Executed real source study

The actual new model integrates J1 with four external source interfaces, while
retaining all preceding tee and elbow connections. Saved native checks report
103 bodies, 222 owned ports, 97 actual directed links and 28 boundary ports.
ROOT and J2 remain explicitly blocked; all 33 original requirement IDs remain.
The source candidate, parent network and existing DWG/PDF delivery are preserved.

Full raw clash analysis executes under the exact previous policy, with zero
contact waivers or tolerance changes. Geometry coverage passes. Ten unique
intersection pairs reduce to six (12 raw intersection records), associated with
the original ROOT and J2 incidents. This association is not a general causal
proof or installation acceptance. Clearance remains failed: 99 raw records
represent 99 unique pairs. The expanded represented inventory and new interfaces
remain in those results; no failures are omitted to improve the apparent result.

Six source/native regression tests pass, including distinct earlier tee/new
cross trim accounting, saved cross assembly, source coverage/budget rejection,
and interface direction/position/roll rejection. Separate actual saved-model
controls reject a deleted connection and a changed native cross prism section.
See [safe aggregate evidence](evidence/source-cross-network.json).

Independent whole-source/native replay passes on the saved combined model.
The shared D-01 constraint also identifies a deliberate redesign need: with the
currently declared separate maximum-incident equal-section prism cores, ROOT
requires more than 0.6758 m reach and J2 more than 0.6258 m. Their strict combined
lower bound is 1.3016 m before any transition/end-straight allowance, against
0.619416 m available after elbows, plus the retained 0.05 m minimum remainder.
Simply shortening the declared extra straight pieces cannot make this particular
construction fit. This bound does not apply to every compound fitting or changed
route, and does not establish measured installed geometry or product acceptance.
