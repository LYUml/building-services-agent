# Pressure-based searched route

Actual route_optimize execution consumed the three tracked examples/route-search inputs. The physical-length baseline has eight elbows and 5.313274122871834 m length, losing 1.1605120333798988 Pa. The derived pressure objective selects two elbows and 5.828318530717958 m, losing 0.7377512857909303 Pa under the same fixed-bore prescribed-flow assumptions.

The selected five-piece model was actually generated, schema/geometry/port checked and independently reopened for pressure binding. All four saved pressure components were compared with the selection-stage calculation and matched at 1e-12 tolerance. IFC is retained locally in runs/route-pressure-optimisation-v1/selected/bound/bim/model.ifc; its digest is in the verification report. Source inputs are tracked for reproduction. No large mesh file is duplicated here.

Seventeen related tests passed, including the independent laminar pressure formula, extra straight-piece K accounting, retained low-supply failure and rejection of conflicting objectives. This does not prove route self-clearance, obstacle IFC correspondence, product, native drawing or full engineering acceptance.
