# Manufacturer fitting intake

Use a manufacturer record before replacing synthetic tee inputs. The first inspected record is [Victaulic No. 20 DN40](../sources/products/victaulic-no20-dn40.json). It is research input, not a selectable catalogue entry. Its official PDF is hash-pinned; printed pages 10 and 59 were visually reviewed after downloading and rendering. The PDF and full-page images remain in ignored `runs/manufacturer-intake-v1/`, not redistributed here.

## Data boundaries

Store published quantities with units and page locators. Preserve nominal designation separately from mating pipe OD, internal flow diameter and maximum fitting body envelope. A table's rounded metric column is a published value; do not replace it with a more precise-looking conversion of its inch column.

The current tee authoring adapter requires a constant internal radius and a simplified intersecting-cylinder outside wall. Port centre-to-end distances alone do not establish either radius or the physical groove/coupling shape. A coordination placeholder, if requested, must remain distinguishable from an actual manufacturer's solid and cannot pass product clearance acceptance.

For the pressure adapter, establish the pressure stations, flow direction, reference velocity, split range, Reynolds applicability and whether wall friction is included. An equivalent pipe length is not a dimensionless coefficient. The relation `K = f_D * L_eq / D` requires justified reference-pipe diameter, Darcy friction factor and velocity convention; it does not establish that the resulting coefficient meets our complete face-to-face tee contract. Changing the reference velocity requires a squared velocity ratio, with independently justified flow assignments. Do not invent those assignments from the words run and branch.

## Next integration decision

Obtain a compatible pipe/fitting bore specification and manufacturer hydraulic methodology or a separately justified design method before creating a real `tee_selection` candidate. Establish connection allowances and project service/pressure/temperature suitability separately. Hong Kong applicability must reference the actual project and rule pack; a manufacturer's catalogue is not regulatory approval.

The current record deliberately has null unresolved fields and no solver-ready K values. Existing synthetic regression fixtures remain mathematical controls. This intake is manual source review; no automatic manufacturer extraction, readiness gate or engineering acceptance is claimed.

## Native manufacturer block reuse

The [official software library](https://www.victaulic.com/resource-software/) provides CAD and STEP content under its own license, not an open-source license. A local trial downloaded the IPS AutoCAD 3D package, identified the target instance by its handle, block name and attributes, then extracted its named definition with native WBLOCK. No manufacturer DWG, DXF, PDF preview or model-derived geometry is redistributed. Source URLs/hashes and a limited execution summary are in [the trial record](evidence/manufacturer-block/trial.json).

Reusable original adapter:

```powershell
.venv/Scripts/python -m bsa.cad_block path/to/library.dwg path/to/selection.json --out runs/new-block
```

The selection JSON requires `source`, `drawing_sha256`, `insert_handle`, `block_name`, `insunits`, and a nonempty `attributes` mapping. Obtain the handle and actual values from `bsa.cad_intake`; match them to the source document before selection. Hash mismatch, missing identity, wrong units/attribute values, duplicate tags, nested references and xrefs reject. Output must be a new directory inside this repository. The adapter does not download content or grant redistribution rights.

AutoCAD runs on isolated copies and verifies the active path before writing. A second native process reopens the extracted DWG. Checks cover unchanged input bytes, drawing units, entity type/layer counts and attribute definitions. These are **structural checks, not ACIS shape equivalence**. Output uses the block definition coordinate system; source instance translation, rotation, scale and attached attribute overrides are not baked into it. Instance attributes are retained separately in the report.

The actual target extracted successfully. An additional native MASSPROP probe and fit-to-page isometric wireframe PDF review were performed locally; the tee is visible without clipping. Those are diagnostic observations, not a scaled installation drawing or proof of bore connectivity. The existing idealized IFC tee adapter cannot ingest the manufacturer's ACIS solid yet. Next work is verified solid/port interpretation and model placement, alongside hydraulic methodology; do not overwrite the unresolved product fields with inferred values from a block label.
