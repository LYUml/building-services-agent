# Explicit spatial terminal candidate replay

Reuse decision: compose existing spatial_air_allocation.run and
spatial_terminal_performance.run. Existing source replay,Shapely allocation and
pinned fluids1.3.1 catalogue interpolation stay authoritative. No new solver,
upstream dependency or claimed optimizer. Existing licenses remain unchanged.

Run `python -m bsa.spatial_terminal_revision ORIGINAL --basis BASIS
--products PRODUCTS --out NEW_FOLDER` on one line. ORIGINAL is a verified
terminal-performance.json;BASIS declares complete sourced terminal positions and
turndown for the same rooms;PRODUCTS maps every new terminal to sourced product
settings. Both schemas are the existing spatial allocation/performance schemas.
A new allocation and performance run are created and source-replayed. The
original balance must remain exactly the same source. Original runs are never
rewritten. All paths stay in the repository or explicit selected project.

candidate-comparison.json pins original ancestry,basis,product sources and method.
`verify(folder)` verifies both producers,their declared input links,and replays
the comparison. Output conflicts and result tampering reject. Failed attempts
may retain partial producer outputs for diagnosis;use a fresh output afterward.
This standalone study does not modify the originating workflow or accept its
requirements. There is no automatic CAD update or preferred design selection.

Executed synthetic trial: three rooms with explicitly declared alternative
interior points,six outlets instead of three,same870.4L/s total. The same
archival source-bound product has zero out-of-range cases instead of two.
Native/MOOSAS comparisons match. Coordinates are synthetic design choices,
not measured installations or optimized air coverage. ADPI,room loads,acoustics,
physical routing,fan duty,HK applicability and full acceptance remain pending.
See evidence/spatial-terminal-revision.json.

Five focused tests pass,covering source replay,result tampering,immutable
baseline,existing output rejection and upstream performance controls.

Broader regression:26 related tests pass with the actual MOOSAS runtime enabled.
