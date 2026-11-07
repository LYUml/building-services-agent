---
name: mep-electrical
description: Create source-linked electrical device/circuit data, calculate single-phase loads and conditional cable checks, and author editable CAD overlays for building services designs.
---

# mep-electrical

Use docs/PROJECT_FORMAT.md. Populate equipment and circuit data from the brief, inspected geometry, measured routes and authoritative references. CLI: bsa validate <project.json>; bsa run <project.json> --out <new-run-directory>.
The calculation engine uses sum(kW/PF)*1000 for connected VA, demand VA / line-neutral V for Ib, tabulated ampacity times correction factor for Iz, and mV/A/m * Ib * route /1000 for voltage drop. Mixed load VA summation is conservative scalar aggregation, not a phasor solution. This slice covers single-phase circuits only; do not map three-phase loads to it.
Review Ib <= In <= Iz and voltage drop, then independently address fault disconnection, breaker breaking capacity, overload conventions, coordination, neutral/harmonics, incomer demand and earthing as applicable. No table values are embedded; cite chosen coefficients and conditions. Failed checks require changes, not an unchecked report.
DXF is a metre-coordinate overlay. It does not prove native DWG fidelity or lighting photometry. For native AutoCAD work, verify active document full path immediately before every write; use a versioned copy. Prove units, layers, scale and a three-device sample with actual save/reopen and plot review before mass placement. Keep unsaved user documents open; do not restart CAD.
Generate schedules and diagram labels from the same IDs. Reconcile geometry counts with device data after native authoring.
