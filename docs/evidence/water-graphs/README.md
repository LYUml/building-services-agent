# Executed water graph evidence

Generated 2026-11-08 in this repository with WNTR 1.5.0 and its bundled EPANET runtime, which returned version 20200. The DLL SHA256 and installed NumPy/SciPy/pandas versions are in each raw.json and water.json. No native library is redistributed here. Exact copied notice hashes are in notice-hashes.json.

Full local regression: 142 tests passed in 116.078 seconds, no skips, with AutoCAD 2027, EnergyPlus, Radiance and OCR optional checks enabled (regression.log). All 23 source-linked example plans validated. An independent checkout-index snapshot imported its own staged source and successfully executed/verified the new water workflow. CI configuration now includes a Linux water-runtime job; that remote job is not claimed as observed evidence here.

`positive/` is the actual `water_network` workflow task from examples/water-loop/plan.json. Source data and original input digest are embedded in water.json. Its ten implemented check groups passed. The symmetric diamond produced approximately 2 L/s per upstream branch, +/-1 L/s on the two terminal paths, and pump flow 4.000049 L/s at head gain 44.999691 m.

`weak/` uses the retained weak-source.json, changing only the synthetic pump curve. The native engine converged cleanly, the demand law and other numerical checks passed, but pressure/delivery targets failed. Terminal C received 0.623665 L/s of the 2 L/s design demand (31.18%), with static pressure head 6.458594 m against its 20 m target. This failed case is not replaced by the passing result.

Each directory contains selected raw engine evidence: native INP/RPT/BIN, node pressure/demand and link flow/velocity CSV, raw JSON, summary, log and HTML. Original run artifact inventories name additional unarchived CSV/source-copy files; these directories are selected evidence, not portable complete workflow archives. The complete original runs are under ignored runs/epanet-evidence-v1. No physical route, drawing or BIM visual acceptance is asserted.

The RPT records engine analysis settings; numeric node/link results are in BIN and CSV because native tabular reporting is disabled. Small legacy flow-conversion/float discrepancies remain visible. Runtime source-commit equivalence, general independent pipe energy proof, actual product/route applicability, efficiency/NPSH and domain acceptance remain pending. See ../../WATER_GRAPHS.md.
