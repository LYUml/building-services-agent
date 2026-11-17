# Lighter HVAC installation profile

Use `.[reports,network,spatial]` for the existing interpreted 2D HVAC package.
Add `mcp` for protocol access and other domain extras only for the tasks selected.
The full `gis` and `section` profiles remain available for their own plotting,
IFC and section workflows. No numerical or drawing feature was removed.

The new spatial extra reuses Shapely 2.2.0 and NumPy 2.5.4, already pinned in the
GIS profile. Previously, the HVAC guide recommended GIS even when no Matplotlib
plot was used, and a missing Shapely import recommended the substantially broader
section profile. The guide and error hint now select spatial. Upstream geometry
algorithms and their existing licenses/attribution remain unchanged.

Two fresh Windows environments installed old and new profiles from the same
working source. All common distribution versions match. Site-packages files
excluding bytecode caches total 239,198,010 versus 213,639,960 bytes: a reduction
of 25,558,050 bytes, or 10.68%. Native engines, source checkout and Git history
are outside that measurement. This is installed dependency disk space, not a
claim about solver speed or whole-process memory. Seven distributions associated
with Matplotlib are absent; IFC/Manifold are absent in the new profile too.

The new environment executed the complete seven-stage isolated actual-project
scenario described in REAL_PROJECT_REVISION.md. It saved/reopened AutoCAD DWG,
generated the report, and passed independent package inspection with no stage
errors. All 47 selected section rows and the complete allocation equal the
earlier full-development-environment execution. Every report page's extracted
text matches. The actual A1 and report page 17 rendered PNGs are byte-identical
to the images already viewed. Native correspondence covers 718 entities;
the 23-page PDF checks 388 numerical rows. Engineering status remains
review_required. This profile does not add manufacturer equipment acceptance.

The fresh environment also passes pip check and 26 allocation, duct, terminal
and missing-dependency controls, with no skips. CI now checks the same lightweight
profile and verifies that Matplotlib/IFC/Manifold are not present; its new remote
result is pending. Local native execution remains separate from Ubuntu CI.
See [aggregate measured evidence](evidence/hvac-light-profile.json).
