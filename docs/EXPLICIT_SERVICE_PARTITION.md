# Explicit service-cell allocation

`bsa.air_allocation.prepare` accepts optional keyword arguments `service_cells`
(terminal ID to planar-metre GeoJSON polygon) and `service_basis` (required design
basis). The default nearest-centre behavior is unchanged. Source-bound allocation
project JSON also accepts these two fields together; the existing
`python -m bsa.air_allocation project.json --out fresh-output` command executes
them and binds the complete project, boundary and optional reference hashes.
Missing either optional field is rejected before output is created. No new MCP
tool or independently verified desktop MCP capability is claimed.

The thin adapter reuses pinned Shapely2.2.0 clipping and union, preserving source
column voids. It rejects gaps, overlaps, duplicate/missing identities, invalid
polygons and cells that exclude their terminal. Declared rectangles may extend
beyond the source boundary; only the clipped area receives load. The existing
classified load calculator distributes total flow by clipped area and verifies
area and flow conservation. Explicit cells remain a design assumption, not proof
of measured spatial load, air coverage or ADPI.

Actual separate BSE3227 manufacturer candidate: 64 geometric cells and192 area/
maximum/minimum-flow values match the previous independent strip calculation.
Eleven targeted tests pass, including column exclusion, ID ordering, unequal
service areas and rejection of gaps/overlaps. See
[executed receipt](evidence/explicit-service-partition.json). The subsequent actual
64-terminal CLI execution preserves all64 geometries and192 area/flow values,
binds three input files, and passes14 related tests.

The existing `bsa.classified-air-allocation` provider now also replays explicit
cells and their basis during independent evidence verification. Its earlier
nearest-centre-only replay was corrected, and its acceptance scope now describes
declared service areas. Actual64-terminal provider execution and source replay
pass;22 combined targeted tests pass. This does not claim that a desktop MCP
session has reloaded or executed the change, or that downstream design is accepted.
