# Nominal duct plan projection

`bsa.duct_plan_clearance.run(drawing, schedule, binding, specification, output)`
checks flat-ended straight nominal-width duct footprints against supplied obstacle
polygons. It reuses pinned Shapely geometry, ezdxf source handles and the existing
duct schedule/binding contracts. This is a planar diagnostic, not a three-dimensional
clash solver or proof of installation clearance.

The specification has exact fields drawing_sha256, schedule_sha256,
binding_sha256, clearance_m, basis and obstacles. Each obstacle has id, polygon_m
(finite metre XY coordinates), source_handles and a source interpretation reference.
Positive-area valid polygons must match the actual saved LINE union or straight
closed LWPOLYLINE outline within1e-8m in Hausdorff distance and boundary length.
Open/curved/nonplanar outlines, reused handles, unknown units and changed geometry
reject. Do not invent a closing edge to fit an interpretation. Geometry is confined
to the drawing's XY plane at zero elevation.

Sections must exactly cover a passing computed schedule and bound saved LINEs;
the source endpoints are freshly compared. Nominal width is taken from that
schedule, not inferred from centreline graphics. Each pair records area/distance
and projected_overlap, touching, below_planar_target or clear_in_tested_projection.
The explicit target is a supplied design diagnostic, not a code value. Zero target
screens overlaps/contact only. Entirely clear tested pairs still leave
status=review_required and design_accepted=false. Missing obstacles, wall/insulation
thickness, fitting envelopes, heights and physical clearance are outside this tool.
Do not substitute selected nominal width for an authenticated outer envelope.

Use a new JSON output outside inputs. All four source hashes and the generator hash
are retained; changed sources reject. This standalone post-processing is not a
registered workflow gate and does not independently rerun the sizing solver or
authenticate obstacle interpretation. Verify the producing workflow and its source
correspondence separately before using saved artifacts.

Eight focused plan/arrow/sheet tests pass, including independent overlap-area and
gap calculations in metre/millimetre drawings, contact versus target, changed
source/binding, open outlines and failed-selection controls. Actual private
post-processing verified47 sections against eight closed source-bound columns:
376 pairs have no nominal projected overlap/contact. The ninth interpreted column
is an open source polyline and stays unresolved. One prior rounded outline was
reconstructed from its exact four saved source LINEs without editing the original
record. Walls and full obstacle completeness remain unresolved; no full clearance
acceptance is claimed.
