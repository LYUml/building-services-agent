# Source-classified logical terminal inlets

Reuse decision: compose existing IfcOpenShell0.8.5 system.add_port,
system.assign_system and geometry.edit_object_placement APIs already used by
bsa.bim,plus circular_geometry.frame. No new geometry or connector engine.
Existing upstream licenses/attribution remain unchanged.

`python -m bsa.spatial_terminal_inlets TERMINAL_IFC_REPORT --basis BASIS --out NEW`
(one line) inherits exact verified terminal-ifc.json and its saved model. BASIS
must cover every terminal with offset_m,outward_axis,diameter_m and system.
The first three are source-classified value/unit/source/classification records;
offset has three local SI metres,axis a cardinal outward unit vector (unit1),
diameter a positive nominal metre value. System has id,predefined_type
(AIRCONDITIONING or VENTILATION),source and classification. Repeated system IDs
must have identical basis. Unknown positions,diameters and systems are not filled.

The nominal circular inlet must fit its declared outward envelope face. Saved
world position/axis comes from the actual terminal placement and SI conversion.
A logical IfcDistributionPort SINK/DUCT and declared system grouping are added.
Every original IFC entity and body remains unchanged. Port diameter and complete
basis are source-linked properties;the envelope gains no hole,neck or physical
connector geometry. No new IfcRelConnectsPorts relation is permitted. System
grouping is not a connected network or equipment selection.

Stable GUIDs derive from retained project identity plus terminal/system IDs,
not serialization timestamps. Header-only rewrites preserve identity;different
projects produce different GUIDs. Existing GUID collisions reject. Native saved
schema/EXPRESS,port count/owner/name/direction/type,world point/axis,diameter,
system membership,original entities and unexpected links are checked.
verify(NEW) replays those checks and exact source/method/output hashes.

Actual native/MOOSAS cases add six inlets and one declared air-system group each.
They preserve equal keyed port GUID/system/geometry records and original entities.
The trial uses explicit top-face design choices and nominal0.2032m from the
inherited archival8inch catalogue neck. Nominal diameter is not a measured bore;
port location/orientation are synthetic choices,not manufacturer connector data.
See evidence/spatial-terminal-inlets.json.

Physical body openings/necks,joints,duct routing,network continuity,manufacturer
connection fidelity,visual BIM review,pressure and complete engineering acceptance
remain unfinished. Automatic workflow integration is pending. Existing preview/
coordination ancestry is not silently redirected to this new file;consumer
integration must bind this exact new producer and preserve its limitations.

Validation:6 related tests pass,including header-independent stable identity,
wrong direction after rewritten IFC hash,invalid face/diameter/axis/source,
missing basis,existing envelope preservation and native preview regressions.
