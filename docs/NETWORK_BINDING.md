# Port-derived network geometry

The `network_coordination` workflow joins model authoring to pressure analysis. Run the fully synthetic fixture:

```powershell
python -m pip install -e ".[network,bim]"
python -m bsa.workflow execute examples/network-binding/plan.json --out runs/port-network
python -m bsa.workflow verify runs/port-network
```

Alternatively use `python -m bsa.network_binding <network.json> --model <model.json> --binding <binding.json> --out <new-run>`. This uses the existing IFC envelope and circular prescribed-demand network contracts. No new upstream implementation is copied; IfcOpenShell and fluids retain their existing attribution in THIRD_PARTY.md.

The network input omits all node elevations and segment lengths/diameters. A separate binding maps every node to a model port and every hydraulic segment to an ordered nonempty list of distinct model duct/pipe devices. Each device must have exactly one inlet and outlet at opposite axis-aligned envelope end-face centres, with an explicit source-backed `InternalDiameter_m` scalar property. This property means internal circular diameter, not bounding-box width. The model's device provenance must support the diameter and geometry. The example is synthetic, not manufacturer data.

Chain pieces must have coincident, explicitly connected ports in one system and one duct/pipe class, with constant internal diameter. Node boundary connections must match the bound node device and coordinate, allowing multiple coincident ports on a junction device. Unsupported diagonals, disconnected chains, repeated pieces, diameter transitions and duplicated numeric inputs are rejected. Length is the sum of straight port-centre distances; elevation is the world Z of the bound node port. K values, demands, roughness, fluid properties and limits remain explicit network inputs. No fitting K, bend radius or unmodelled physical length is inferred.

The adapter authors/reopens IFC using the existing geometry/schema/topology validator, calculates the derived pressure budget and separately reads saved IFC world port coordinates and diameter properties to compare with the derived network. A tamper test changes the saved IFC diameter and confirms rejection. Input and generated-artifact hashes are retained. `network-input.json`, `analysis`, `bim` and `network-binding.json` contain evidence.

This is a geometric binding for the existing prescribed-flow circular tree method, not an arbitrary BIM importer or automatic route planner. Axis-aligned boxes remain envelopes rather than circular product solids. Junction shapes, component K evidence, physical clash/clearance, flow balancing, fan/pump curves, closed loops and professional acceptance remain pending. A successful example's `design_accepted` remains false.
