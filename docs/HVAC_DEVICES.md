# Saved HVAC device identity and result IFC

Optional `binding.hvac_devices` links actual saved IFC equipment to the existing annual PTAC workflow. It validates device/system/space identity, geometry containment and declared ratings before simulation, carries GUIDs into saved OSM, and writes source-bound simulation properties to a separate IFC revision. It does not infer a real product from a generic envelope or establish a routed HVAC design.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/hvac-equipment-plan.json --out runs/hvac-equipment --energyplus tools/energyplus-25.2/EnergyPlus-25.2.0-cf7368216c-Windows-x86_64/energyplus.exe
.venv/Scripts/python -m bsa.workflow verify runs/hvac-equipment
```

The plan authors three synthetic `IfcUnitaryEquipment` envelopes, each in its thermal space and the explicit `AIRCONDITIONING` distribution system. Placement and dimensions are sourced synthetic inputs, not manufacturer shape. The scenario derives its saved rating properties from the supplied PTAC input values when preparing the example files; runtime binding independently compares the saved values to the analysis input. If either copy changes alone, binding fails. Universal common-data authoring and automatic product/geometry selection remain pending.

## Binding contract

Keep the existing `source`, `north_axis_deg` and complete `spaces` mapping. Add `hvac_devices`, containing exactly one `{zone_id, device_guid, system_guid, source}` entry per PTAC/thermal space. Zone and device mappings must be unique. Every selected system's saved `IfcUnitaryEquipment` must be mapped; extra unmapped units are rejected. Other system elements do not become implicitly connected air routes.

Each device must be an actual saved `IfcUnitaryEquipment`, contained in the exact mapped `IfcSpace`, and assigned to exactly the specified `IfcDistributionSystem` of type `AIRCONDITIONING`. Names alone do not identify devices. The device must have finite nondegenerate native geometry whose world-coordinate bounds lie inside the mapped space. Metre/millimetre IFC units are normalized by the existing world-geometry reader. The source space audit must have the same IFC hash. These bounds checks do not prove clash clearance, installation access or product geometry.

`BSA_DesignInputs` must contain a nonempty `Source` and all following explicit saved properties. They are independently compared to the PTAC's inputs without converting thermal capacity into electrical input:

| PTAC field | Saved property |
|---|---|
| cooling_capacity_w | PTAC_CoolingCapacity_thermal_W |
| cooling_cop | PTAC_GrossCoolingCOP |
| cooling_shr | PTAC_GrossCoolingSHR |
| supply_flow_m3_s | PTAC_SupplyFlow_m3_s |
| heating_capacity_w | PTAC_HeatingCapacity_thermal_W |
| heating_efficiency | PTAC_HeatingEfficiency |
| fan_pressure_pa | PTAC_FanPressure_Pa |
| fan_efficiency | PTAC_FanTotalEfficiency |
| motor_efficiency | PTAC_MotorEfficiency |
| motor_in_air_fraction | PTAC_MotorInAirFraction |

The prepared annual input adds `ifc_device_guid` and `ifc_space_guid` to each HVAC zone. Both must be valid GUID-shaped strings when supplied. The saved OpenStudio PTAC receives `IFCDeviceGUID` and `IFCSpaceGUID` features, checked on reopen alongside its existing ratings/curve/topology audit. Performance curves remain independently sourced analysis inputs; they are not inferred from IFC capacities.

## Property-only analysis revision

The original source is copied unchanged to `model.ifc`. `analysis.ifc` is the canonical IFC artifact passed by `annual_energy_ifc` to downstream workflow tasks. With no device mapping it is an unchanged copy. With mapping, it adds a new reserved `BSA_PTACSimulation` property set to each selected device. Existing result property sets are rejected to preserve earlier revisions.

New properties record thermal-zone/device/space identity, source IFC hash, annual report hash, engine version, calculated-check status, `DesignAccepted=false`, and baseline/variant simulated annual electricity kWh and maximum hourly electricity kW per PTAC. That peak is a modeled hourly operating peak; it is not an equipment electrical nameplate, instantaneous start demand, protective-device or feeder design value. No existing `ElectricalInput_kW`, design rating, geometry, system or connection is overwritten.

After saving, the adapter reopens the result IFC, compares every original STEP entity by identity and serialized content, verifies all new properties and runs IFC schema/EXPRESS validation. Added property entities/relationships are permitted; original entities must remain unchanged. Source bytes and all output artifacts are hash checked. These checks establish a property-only revision and traceability, not viewer or engineering acceptance.

Failed annual targets remain failed in both the workflow and added IFC status properties. The derived model may retain useful failed analysis quantities, but `CalculatedChecksPass=false` and `DesignAccepted=false` are preserved; downstream tasks requiring a passing producer stay pending. Tests execute this case with deliberately insufficient heater capacity.

Outputs include `thermal-binding.json.hvac_device_binding`, `annotated_ifc`, saved GUID features, per-device result properties and the existing annual/native artifacts. Detailed products, IFC ports and physical duct routes, equipment clashes/clearances, actual source/code applicability, real-project calibration and BIM-viewer/engineering acceptance remain pending. See [PTAC model limits](THERMAL_HVAC.md), [space binding](THERMAL_BINDING.md) and [attribution](../THIRD_PARTY.md).
