# Manufacturer fitting intake

Use a manufacturer record before replacing synthetic tee inputs. The first inspected record is [Victaulic No. 20 DN40](../sources/products/victaulic-no20-dn40.json). It is research input, not a selectable catalogue entry. Its official PDF is hash-pinned; printed pages 10 and 59 were visually reviewed after downloading and rendering. The PDF and full-page images remain in ignored `runs/manufacturer-intake-v1/`, not redistributed here.

## Data boundaries

Store published quantities with units and page locators. Preserve nominal designation separately from mating pipe OD, internal flow diameter and maximum fitting body envelope. A table's rounded metric column is a published value; do not replace it with a more precise-looking conversion of its inch column.

The current tee authoring adapter requires a constant internal radius and a simplified intersecting-cylinder outside wall. Port centre-to-end distances alone do not establish either radius or the physical groove/coupling shape. A coordination placeholder, if requested, must remain distinguishable from an actual manufacturer's solid and cannot pass product clearance acceptance.

For the pressure adapter, establish the pressure stations, flow direction, reference velocity, split range, Reynolds applicability and whether wall friction is included. An equivalent pipe length is not a dimensionless coefficient. The relation `K = f_D * L_eq / D` requires justified reference-pipe diameter, Darcy friction factor and velocity convention; it does not establish that the resulting coefficient meets our complete face-to-face tee contract. Changing the reference velocity requires a squared velocity ratio, with independently justified flow assignments. Do not invent those assignments from the words run and branch.

## Next integration decision

Obtain a compatible pipe/fitting bore specification and manufacturer hydraulic methodology or a separately justified design method before creating a real `tee_selection` candidate. Establish connection allowances and project service/pressure/temperature suitability separately. Hong Kong applicability must reference the actual project and rule pack; a manufacturer's catalogue is not regulatory approval.

The current record deliberately has null unresolved fields and no solver-ready K values. Existing synthetic regression fixtures remain mathematical controls. This intake is manual source review; no automatic manufacturer extraction, readiness gate or engineering acceptance is claimed.
