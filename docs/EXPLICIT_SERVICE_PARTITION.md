# Explicit service-cell allocation

`bsa.air_allocation.prepare` accepts optional keyword arguments `service_cells`
(terminal ID to planar-metre GeoJSON polygon) and `service_basis` (required design
basis). The default nearest-centre behavior is unchanged. CLI/MCP project schemas
are unchanged; this is a Python composition API.

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
[executed receipt](evidence/explicit-service-partition.json).
