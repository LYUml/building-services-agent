# Verification record

2026-11-08 foundation milestone, Windows / Python 3.12.

- Editable package installation succeeded in this repository's .venv.
- `python -m unittest discover -s tests -v`: 4 tests passed. Covers hand calculation, rejection of invalid provenance/topology/numbers, visible cable failures, artifact counts, immutable input and overwrite refusal.
- `python -m bsa.cli run examples/office-electrical/project.json --out runs/office`: executed; calculated checks pass; design_accepted remains false.
- Three synthetic device circles exported, source JSON hash unchanged.
- No native AutoCAD, IFC, EnergyPlus or photometry execution yet. HTML/SVG generated but visual review is pending. No full engineering/design acceptance is claimed.

Run directories are excluded from Git; regenerate them from the tracked example. The current overall goal remains active; see ROADMAP.md for unfulfilled requirements.

Follow-up checks: all five skills passed the host skill-creator validator after installing its PyYAML prerequisite. DXF serialization now uses pinned ezdxf 1.4.5 with explicit metre units and declared layers. Independent reload verified three circles, three labels, units=metres and zero audit errors. Four tests passed again; the updated sample ran in runs/office-v2. AutoCAD 2027 and Revit 2027 installation directories are present; live/native integrations have not yet been executed.
