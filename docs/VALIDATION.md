# Verification record

2026-11-08 foundation milestone, Windows / Python 3.12.

- Editable package installation succeeded in this repository's .venv.
- `python -m unittest discover -s tests -v`: 4 tests passed. Covers hand calculation, rejection of invalid provenance/topology/numbers, visible cable failures, artifact counts, immutable input and overwrite refusal.
- `python -m bsa.cli run examples/office-electrical/project.json --out runs/office`: executed; calculated checks pass; design_accepted remains false.
- Three synthetic device circles exported, source JSON hash unchanged.
- No native AutoCAD, IFC, EnergyPlus or photometry execution yet. HTML/SVG generated but visual review is pending. No full engineering/design acceptance is claimed.

Run directories are excluded from Git; regenerate them from the tracked example. The current overall goal remains active; see ROADMAP.md for unfulfilled requirements.
