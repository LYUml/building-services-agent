# Logical supply network to80terminal connections

The separate664element outlet candidate previously contained81flow components.20existing casing envelopes now have IfcAirTerminalBox USERDEFINED roles and20Jplenum envelopes have IfcDuctFitting JUNCTION roles,with140new owned source-positioned ports and120new logical connections.604distribution products/1287ports/603interfaces now form one acyclic logical tree from one main inlet to80terminal connection planes. A declared unified distribution-system membership covers604products. Existing80routes and source files are preserved.

Both prescribed design-flow cases reconcile every1287port. Maximum flow remains12.000372763m3/s;minimum4.800149105m3/s. This is conserved source demand,not pressure-balanced operation or commissioning. No duplicated main/downstream source sum is used.

## Physical scope

All664native representation values and world placements remain identical to the previous shared model.40reclassified equipment meshes are actually read back and match the source meshes. Existing604body/envelope collision evidence is reused by this explicit geometry-identity handoff;it is not presented as fresh whole-model remeshing. Source IFC and revised IFC both remain separate. Revised schema/EXPRESS passes.

The inherited device solids remain outside coordination envelopes,not fabricated walls or open internal airways. New logical connections reconcile owned port centres/opposite normals,but do not certify material caps,sealing or collar insertion.140new device-port clear areas and velocity pressures remain null. They are not inferred from nominal/outside dimensions.

Pinned2021LMHS catalogue A2-7 is actually viewed: A3.375in andL15.5in are consecutive spans;the logical discharge datum usesA+L. A published0.5in discharge lip and actual slip-drive overlap are not modelled. Standard/optional liner and control choices exist;none supplies an accepted internal area or whole-device loss here. Joutlet positions use the previously reviewed A2-10/11dimensions. The catalogue SHA remainsba747af8d424da4e59b0d4d93c888bd9b5df299d303c0824fa89f9305870d766.

## Expanded pressure evidence

Existing source-tree path reconstruction and source_pressure_ledger now execute across the represented604product tree.225straight spans and458directed nonstraight component paths cover all80terminal connections. Each flow case contains194conditional numerical component values and264unresolved directed paths. Missing classes are4compound-main paths,20VAV device losses,80Jplenum paths and160outlet bends. Each outlet has5unresolved component paths;all complete pressure values,critical path and fan duty remain null. These are expanded coverage counts;the earlier114/4main result applied only to164main bodies.

114main conditional values are reused only after exact main native geometry/placement and347source-flow correspondence plus independent parent-ledger reconstruction.80reducer values are rebound to actual source flow/native reference velocity. Downstream straight friction uses explicitly assumed smooth rigid-equivalent geometry;the earlier unselected TripleLock chart comparison remains separate. Parallel outlet paths are never added. Equipment minimum operating static is not automatically total-pressure loss. Physical joints,body friction,interaction,actual elevations,selected product/control/liner and diffuser discharge pressure remain unresolved.

## Reusable interface evidence guard

boundary_paths now propagates optional interface_basis and physical_cap_verified fields into saved path steps. The legacy shared_cap_interface kind denotes graph adjacency;it is not a physical receipt. A logical_equipment_connection cannot claim physical_cap_verified=true. Missing logical evidence stays not verified,and nonboolean claims reject. Unannotated historical input keeps its original numeric/path representation.

source_pressure_ledger reconstructs these annotated steps,exposes120logical equipment interfaces globally and3per terminal path,and retains physical_airway_continuity_verified=false. Erasing saved path evidence fails reconstruction. No pressure acceptance is inferred from graph completion. Fresh outputs are in private pressure-interface-evidence;older full-network receipts are historical after this method change.

Seven actual-network controls plus existing chain/ledger tests execute:15tests and20subtests pass. The old main-only numerical result still reconciles exactly. Tests cover false physical-cap claims,nonboolean evidence,missing evidence,erased steps and140unknown device areas without mutation. No full repository-suite result is claimed.

## Native drawing and delivery

The actual reopened DWG contains all604distribution GUIDs:164main material sections,80reducer material sections,320branch-axis products and40equipment envelopes.80branch route vertices,40equipment footprints,80reducer profiles and20VAVtag identities independently reconcile to the revised saved IFC.120dashed schematic axes express logical device flow,not manufacturer internal duct routes.100labels are placed with measured font boxes and pinned Shapely STRtree. Actual saved PDF is rendered/viewed with no observed clipping.

Course deliverables are Logical_Supply_Network/Supply Air Logical Network.ifc,dwg,pdf;160terminal pressure rows,20equipment connection rows,an HTML review and derived JSON. Evidence: docs/evidence/logical-supply-network.json. Internal runtime/PDF/images/source archives remain private. The full project goal is unfinished.

Reuse: pinned official IfcOpenShell0.8.5 class/port/system APIs,existing prescribed_flows,boundary_paths,source_pressure_ledger and isolated AutoCAD/ezdxf tools. The existing hvac_devices PTAC adapter was inspected and not adopted as a VAV rating engine. No new solver,dependency,rating source or separate KSelect MCP is introduced. This remains an executed project composition,not a new registered generic producer.
