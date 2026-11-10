# Source-declared centred rectangular transitions

`bsa.rectangular_transition` is a thin adapter around pinned IfcOpenShell0.8.5
ShapeBuilder.mep_transition_shape, faceted_brep, native Boolean and port APIs.
The upstream fitting investigation and executed limitations are recorded in
MEP_FITTING_REUSE.md. The helper generates filled outer geometry; this adapter
explicitly creates an inner air volume and subtracts it to form a wall.

```powershell
.venv/Scripts/python -m bsa.workflow execute examples/rectangular-transition/plan.json --out runs/rectangular-transition
```

Standalone authoring is also available:

```powershell
.venv/Scripts/python -m bsa.rectangular_transition examples/rectangular-transition/project.json --out runs/rectangular-transition-standalone
```

All inputs are explicit: canonical project_uuid, source, classification, sourced
right-handed rigid placement, start/end inside width-height pairs in metres,
section_offset_m, positive start/end straight lengths, upstream_angle_degrees,
transition_length_m and two port directions. Classification is given, assumed or
secondary_transcription. Directions are opposed SOURCE/SINK or both SOURCEANDSINK.
The two sections must differ. No taper length, product dimension or regulatory
angle is selected automatically. A disagreement between the source taper length
and upstream shape fails; diagnostic upstream.log remains available.

`wall_model` must explicitly be section_plane_offset. The same offset is added
to each side of the inside end rectangles and linearly carried through the taper.
This is **not constant sheet-normal thickness on sloping faces** and cannot be
used as authenticated fabrication construction or a nominal product sheet gauge.
Profiles remain centred, sharp and untwisted; eccentric/round/filleted transitions
and joints are unsupported. The upstream angle is independently checked as the
maximum included angle in the two centred section planes. It is not an inferred
code or loss limit.

The inner volume extends0.1mm beyond each cap solely for Boolean construction;
inner and outer taper stations remain coincident. Straight lengths must exceed
that extension. This does not change physical model bounds or create an installed
joint allowance. Existing upstream holder segments/representations are removed;
the result contains one IfcDuctFitting TRANSITION and two stable owned ports.

Saved checks include schema/EXPRESS, source/wall metadata, proper rigid placement,
native outer-minus-inner BRep structure, finite planar faces and exact source
section corners/stations. Local native mesh material must be positive, connected
and closed with Euler characteristic0. Independent area-polynomial integration
checks material volume and axial centroid; outer bounds and a centre through-bore
probe are checked separately. The probe does not measure minimum clear bore.
Source-preserving hashes, pinned versions, upstream builder hash and logs are
recorded. The current synthetic fixture has0.00435635861m3 material volume.

Workflow kind rectangular_transition accepts only project plus ordinary task
fields/gates. IFC readers inherit transition.ifc through depends_on. The public
workflow executes a saved-model preview; it does not perform a multi-element
clash study. Generated preview arrows are illustrative, with opaque projection
artifacts; the actual four-view preview was inspected for local shape/end openings
only. A preview is not a hidden-line drawing or viewer/installation acceptance.

Native test cases cover reduction, reversed expansion/bidirectional flow and
width-reduction/height-expansion under a translated non-axis-aligned rigid frame.
Saved corner, filled-body operator, port frame/direction and source mutations
reject. Angle/length disagreement rejects independently. Workflow tests verify
the exact inherited IFC hash, pending visual review, source pins, forbidden
replacement input and real upstream length failure blocking the preview. Evidence
is in evidence/rectangular-transition.json.

This enables a reusable local transition component. Complete unequal-section tee
composition, adjacent straight assemblies, source-backed end stations and trims,
real VAV/product ports, pressure losses and regional/installation acceptance remain
pending. The real HVAC layout's15 unequal-section tees are not replaced by this
independent synthetic transition example. design_accepted remains false.
