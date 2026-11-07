---
name: mep-ifc-authoring
description: Create and revise source-linked IFC4 MEP envelopes or explicit straight circular wall solids with spaces, systems, ports and native geometry verification. Use for open BIM authoring and IFC model checks.
---

# IFC MEP authoring

Read docs/IFC_MODELS.md. Use `python -m bsa.bim <project.json> --out <new-run>` or the `bim` workflow adapter. Install the optional `bim` dependencies first. Input examples are under examples/mep-ifc.

Every dimension, origin, device class, containing space, system and connection must come from source data or an explicit scenario assumption. The adapter uses SI metres and axis-aligned bounding envelopes at minimum-corner origins; do not pass centre coordinates or assume actual manufacturer shape. Device rotations, arbitrary routing, multi-system equipment and bidirectional ports are unsupported. Do not synthesize their results through this adapter.

For actual straight round wall bodies, read docs/CIRCULAR_GEOMETRY.md. Opt into the explicit mixed geometry scope and `body_shape: straight circular wall`, with separately sourced internal/outside diameters and opposite end-face-centre ports. The saved IFC must pass hollow-profile, oriented connected mesh/bore, annular volume, bounds and outward-port-axis checks. Preserve the distinction between an analytic IFC wall and its approximate QA mesh, and between this generic straight body and manufacturer/fitting geometry. Never infer a circular body or wall parameter from electrical ratings or a single bounding dimension.

Keep equipment IDs consistent with the calculations and CAD used in the same actual project. The separate synthetic IFC examples are not automatically reconciled with the earlier three-light CAD dataset. Preserve source descriptions and electrical input kW; never label thermal capacity as electrical input.

Port connections represent explicit logical topology, not a routed or sized pipe/cable. Provide local port offsets and source-to-sink directions. Read bim-verification.json and schema-validation.json after native IFC reopen. They check entity counts, source properties, space/system membership, world-coordinate envelope bounds, metre units, port direction/placement and connection endpoints. Schema/EXPRESS validity does not prove physical feasibility, performance or code compliance.

Inspect the model in a BIM viewer and record artifact-hash-bound visual evidence before claiming visual acceptance. Keep detailed shape, clash/routing, system performance and domain compliance pending until actually verified. Do not claim RVT fidelity from an IFC result.

For revisions, supply a canonical `project_uuid` to keep class/input-ID object and device/port GUIDs stable. Retain that namespace for the same project and use a new UUID for an independent project. Do not promise stable relationship/representation IDs or byte-identical IFC files. For geometry-linked network sizing, use docs/NETWORK_MODEL_DESIGN.md with explicit outside dimensions; it preserves source endpoints and checks the new saved IFC against selected calculations while keeping product and visual gates pending.

For electrical devices already defined in the common electrical schema, prefer the coordination adapter documented in COORDINATION.md instead of retyping electrical values into a separate BIM project. It converts centre XY to minimum-corner envelope origins, propagates circuit/power/PF/source properties and checks saved IFC against DXF and calculations. Its companion geometry must explicitly supply dimensions and elevation; none are inferred from electrical ratings.
