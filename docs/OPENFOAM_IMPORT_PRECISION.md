# Native OpenFOAM mesh import

The existing main mesh now imports through the official blueCFD-Core 2024-1
OpenFOAM 12 native gmshToFoam utility, build 12-8e8552546d20. Runtime files were
extracted in an isolated directory using innoextract 1.9; no installer scripts,
system MPI, file associations or context menus were applied. Child-process
environment selects serial dummy Pstream. OpenFOAM is GPL-3.0-or-later;
innoextract is zlib/libpng licensed. No runtime binaries are redistributed.

Default ASCII output rounded source coordinates by up to 0.00005 m, exceeding
the approximately 0.00001 m minimum edge. Native checkMesh then detected 14043
negative-volume cells and 41 open cells before a floating-point exception.
The failed case is preserved privately. A separate import of the identical
source with controlDict `writePrecision 17;` preserves all 126183 source points
exactly, all 265741 cells and the six expected patch face counts. No remeshing,
threshold relaxation or geometry change was used. Face areas and cell volumes
are positive; topology and face-pyramid checks pass.

The high-precision mesh still **fails three native quality checks**: high aspect
ratio, small cell determinant and small face interpolation weight. Maximum
non-orthogonality is 74.459 degrees (five faces above 70); these warnings also
remain explicit. No pressure solve or engineering acceptance follows.

checkMesh returns zero despite its `Failed 3 mesh checks.` conclusion. The thin
standard-library `bsa.openfoam_mesh_review.assess_check_mesh` reader therefore
requires an unambiguous `Mesh OK.` and completed `End`, a zero exit code, and no
failure or fatal markers. It changes no native thresholds. Three targeted tests
cover zero-exit failures, terminal success and incomplete/conflicting/crashed
logs; both actual main-case logs replay as not passed. This reader is scoped to
a single serial OpenFOAM 12 checkMesh invocation, not arbitrary log aggregation.

Executed values are in [the sanitized receipt](evidence/openfoam-import-precision.json).
Private meshes, logs and workstation paths remain excluded from public snapshots.
Both existing plenum families also import without remeshing: 823552 and 869970
cells, respectively. Their 340380 and 359493 points exactly match their source
coordinates. Both native checkMesh runs complete but each reports the same three
quality-check categories failed, despite exit code zero. Their positive volumes,
face checks and remaining quality statistics are retained in the receipt.
Next: diagnose the retained layered-cell quality and establish a source-backed
solver benchmark before accepting project pressure results.
