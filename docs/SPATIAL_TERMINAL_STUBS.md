# Explicit terminal inlet short-stub study

Reuse decision: compose existing circular_geometry.author/specification/verify,
IfcOpenShell0.8.5 system.add_port/connect_port and the saved inlet producer.
Reuse the existing circular frame and closed hollow-wall mesh/volume checks;
no new geometry,connector or hydraulic solver. Existing attribution/licenses
remain unchanged. The reused circular authoring path requires metre-unit IFC;
other source units reject rather than silently mis-scale.

`python -m bsa.spatial_terminal_stubs INLET_REPORT --basis BASIS --out NEW`
(one line) requires verified terminal-inlets.json. BASIS covers every terminal
with positive length_m,internal_diameter_m and wall_thickness_m records,each
value/unit m/source/classification. Position,outward axis,nominal inlet diameter,
system,space and maximum/minimum L/s flow are inherited from saved native evidence.
Direct bore must match nominal inlet in this bounded study. This matching
assumption does not authenticate actual bore,manufacturer geometry or joint fit.
No source route length,offset or replacement inlet is accepted.

A straight hollow IfcDuctSegment extends outward by the explicit length.
Its terminal-facing SOURCE port coincides with and opposes the original SINK
inlet;the new upstream SINK remains unconnected. Both ports and the body have
stable project/component IDs. One directed same-file link is added per terminal.
Existing entities,flows,systems and body geometry are unchanged. New duct bodies
join the declared existing system through new relations without rewriting its
original membership relation. IFC spatial containment is inherited logical
containment,not proof that the branch stays inside the room/ceiling volume.

Saved reopening checks full schema/EXPRESS,complete new body/port inventory,
original entity preservation,profile radii/gauge/length,closed native mesh and
volume,world body bounds,port ownership/points/axes/system and exact directed
links. Body bounds are checked separately:correct volume/radii alone can miss
an axial displacement of the solid relative to its ports. Source maximum/minimum
flows are preserved in properties without copying caller-supplied replacements.
verify(NEW) repeats source/method/output hashes and full native replay.

Actual native/MOOSAS cases each add6short stubs of0.15m length,0.2032m assumed
bore and0.8mm explicitly chosen wall. These are synthetic study assumptions,
not installed lengths,measured bores,manufacturer gauge or local code values.
Both preserve equal keyed native geometry/flow records and original entities.
See evidence/spatial-terminal-stubs.json.

Validation:10 related tests pass. A shifted body with unchanged volume/radii is
rejected even after rewriting the IFC hash;deleting one directed link also
rejects. Invalid length,bore,wall/source and existing inlet/circular controls pass.

Terminal bodies remain closed bounding envelopes with no real neck/opening.
Thus coincident ports and a hollow stub do not prove physical air passage,
installation or a whole connected supply network. The upstream ends are open.
Full-model clashes/clearances,room/ceiling containment,manufacturer/fitting
geometry,pressure/fan duty,visual BIM and engineering acceptance remain pending.
Existing consumer/workflow bindings are not silently redirected to this new
producer;automatic stub/consumer integration remains unfinished.
