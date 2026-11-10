# Source-bound GIS footprint context

This source acquisition/projection adapter supports candidate context investigation, not parcel selection or building-height inference. It reuses pinned pyproj 3.7.2 / bundled PROJ 9.5.1 in an isolated local runtime, plus Shapely 2.2.0 in the existing repository Python for topology/area validation. GeoPandas/OSMnx were not added: their larger table/network stacks are unnecessary for this bounded polygon/projection gap. Projection and geodesic computation remain upstream implementations. Installed pyproj/PROJ MIT, Shapely BSD-3-Clause/GEOS and certifi MPL-2.0 license texts are retained under adapters/gis-context/licenses; exact isolated dependency versions are pinned.

Restore:

```powershell
.venv/Scripts/python -m pip install -e ".[gis]"
./adapters/gis-context/bootstrap.ps1
```

Fetch a bounded source snapshot and run:

```powershell
.venv/Scripts/python scripts/stage_chicago_footprints.py --out runs/new-chicago-footprints --gis-python tools/gis-runtime/Scripts/python.exe
```

Replay the actual snapshot without networking:

```powershell
.venv/Scripts/python scripts/stage_chicago_footprints.py --out runs/new-footprint-replay --gis-python tools/gis-runtime/Scripts/python.exe --cache runs/chicago-footprints-v2
```

The explicit candidate query window is in benchmarks/mit-4401-2018/gis-decisions.json. Reference 41.888 / -87.648 and the small surrounding WGS84 window are query/design decisions only, not a surveyed project location or selected parcel. Queries use Socrata intersects with a polygon, not a fully-contained footprint filter. Full intersecting polygons are retained without clipping. Separate before/after count queries, a hard 200-record cap, exact distinct IDs/counts and raw response byte budgets prevent a silent partial first page. Query URLs, acquisition time, original response hashes and dataset metadata are retained in snapshot.json. Cache replay rejects different query identity or changed source bytes.

Official source review found that hz9b-7nh8 is a map/visualisation, tf32-rk4u explicitly describes itself as outdated, and the underlying syp8-uezg source metadata says Current as of August 2015. It supplies stories/no_stories/z_coord fields, not a validated current building-height model. The live metadata's later publication/update labels do not make 2015 geometry current. The data license is SEE_TERMS_OF_USE and attribution is City of Chicago: it is not relicensed as MIT project code. Raw/derived source inventories and maps stay in ignored local runs, with source attribution and modified-presentation/no-endorsement labels; consult the City's source terms for redistribution.

A better height source was identified: Cook County GIS Building Footprints 2022, official ArcGIS item 7c4f47a3b32944e58c5f18652880fc05. Metadata describes 2022 LiDAR/imagery, created in 2025, with Ground_Z, Max_Point and above-ground Height. The service's sourceHeightModelInfo specifies NAVD88 height (ftUS) and us-foot. It is not international-foot, metre, storey count or arbitrary floor-to-floor height. Official item metadata/XML downloaded, but actual county geometry queries/direct downloads fail here with TLS unexpected EOF. No certificate checks, host policy or authentication were changed. County geometry/height conversion is not integrated or claimed verified. Metadata identification is not an executed 3D dataset integration.

The executed 2D path passes all original coordinate rings to a local WGS84 azimuthal-equidistant projection, explicitly using always_xy longitude/latitude order. The origin maps to zero; a same-longitude north probe maps to positive Y. Every vertex is inverse-transformed and compared. Parent Shapely checks valid complete multipolygon topology, positive area and consistency with upstream ellipsoidal geodesic area. The 1e-9 degree roundtrip and 1e-4 relative projection/geodesic area bounds are numerical QA targets, not survey accuracy or regulation. local-footprints.json is an explicitly CRS-described projected JSON structure, not RFC7946 geographic GeoJSON.

Actual runs/chicago-footprints-v2 has all 34 intersecting source records. Maximum roundtrip discrepancy is 2.1316282072803006e-14 degrees. Computed projected footprint area sum is 47083.4623537 m2, including complete footprints crossing the query boundary; it is not parcel area, usable area, building GFA or project coverage ratio. All 34 height_m values remain null, and three_dimensional_context_ready/site_selected/design_accepted are false. No storey-height product or zero Z_COORD was promoted to measured height.

The plotted source outlines, origin/reference label, metre axes, north-at-reference marker and 2015/unknown-height limitations were visually inspected. Blank map space cannot establish vacant land, ownership or development availability. Source records can be split or overlapping footprints and are not an independently verified count of physical buildings. Actual parcel selection, current surrounding buildings/trees, vertical datum/ground placement, IFC georeferencing and real shading remain pending. This adapter is currently standalone; it does not change the existing thirteen-task public workflow or clear its fourteen pending engineering packages.

Three tests pass: exact cached replay/IDs/unknown heights/metre scales, source/query mutation rejection, and a deliberately feet-scaled projected geometry that fails the independent geodesic-area check. Evidence: evidence/site-context/chicago-footprints.json.
