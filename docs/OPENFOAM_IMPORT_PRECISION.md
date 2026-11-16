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


## Executed native solver and defect locations

The packaged official pitzDailySteady case now completes native blockMesh,
checkMesh and foamRun under the same isolated serial environment. All copied
case inputs remain byte-identical to the packaged tutorial. The local mesh
dictionary differs from the Allrun shared resource only by its copy comment
and whitespace. An initial absolute Windows -dict path failed native path
resolution; the packaged local dictionary succeeds. Mesh OK and native SIMPLE
convergence at iteration286 are recorded, using unchanged tutorial residual
controls. This is an executed backend smoke check, not physical validation or
project pressure acceptance. See [runtime receipt](evidence/openfoam-native-tutorial.json).

Native -writeSets on the existing first plenum provides actual failed-cell and
face IDs. Cell classification independently counts owner/neighbour face
incidence:256436four-face tetrahedra and567116five-face prisms, agreeing with
native stats. All5552high-aspect cells are prisms. Of250706small-determinant
cells,250702are prisms and4are tetrahedra. All6low-weight internal faces join
tetrahedra. Their vertex-average locations are recorded (not volume centroids).
Thus thin layers explain much of the failure but do not explain all defects;
local tetrahedral quality also needs correction. No threshold was relaxed.
See [location receipt](evidence/openfoam-plenum-quality-location.json).


## Constrained core and prescribed outlet flow

Extracting the original256436tetrahedra with38234explicit boundary triangles
and reclassifying nodes lets pinned Gmsh4.15.2 operate on the core while fixing
the prism interface. Relocate3D changes22843internal nodes only; source surface
and all volume connectivity are unchanged. Native minimum interpolation weight
improves0.0245058to0.0306360, but six failing faces remain. A separate default
tetrahedral optimizer with threshold0.8 (an optimization target, not a native
check relaxation) yields246504tetrahedra with all567116prisms and core boundary
faces preserved. Native low-weight failures decrease6to4 and small-determinant
cells250706to250705. Three failed check categories remain. All volumes remain
positive and total volume matches source within1.4e-15m3. Netgen changes core
boundary connectivity and is rejected before export. No pressure acceptance.
[Executed candidate receipt](evidence/openfoam-constrained-core.json).

A separate adaptation of the already-executed official pitzDailySteady case now
executes flowRateOutletVelocity at0.000254m3/s (positive outward). All pressure
patches use zeroGradient with pRefCell0/pRefValue0. Native surfaceFieldValue
signed phi sums over200consecutive iterations290..489 give maximum relative
outlet error and global imbalance1.0672e-15. Independent polygon-area integration
of saved400U yields0.00025399999999999994m3/s. The1e-10 comparison target checks
boundary algebra, not physical accuracy. Native initial convergence occurs289;
its original loose residual stopping is then removed solely to collect a fixed
200step observation window. No pressure-stability or physical-validation claim.
OpenFOAM12 reads system/functions ahead of controlDict/functions; the initially
ignored observer is preserved and corrected. End489fields were not written under
the inherited100step cadence, so independent checking uses saved400within the
window. Multi-outlet operation and actual project physics remain unverified.
[Executed flow receipt](evidence/openfoam-prescribed-flow.json).


## Two independently prescribed outlet patches

The same official tutorial mesh has its57outlet faces partitioned into30and27
faces without changing points, faces, owner or neighbour arrays. Targets are
one-third and two-thirds of0.000254m3/s; these are explicit numerical test values,
not project design inputs. Mesh OK and600native steady steps complete. Over
steps401..600 each target is met within6.403e-16relative and signed global
imbalance within5.870e-16. Independent600U polygon-area integration agrees for
both patches. This tests two independently controlled boundary partitions on
ONE outlet, not actual separate duct branches or physical pressure accuracy.
[Executed two-patch receipt](evidence/openfoam-two-outlet-patches.json).

The stdlib bsa.cfd_flux_window.assess_flux_window requires conservative signed
targets, exact finite named fluxes and a complete consecutive integer-step
window. It checks each branch and signed total, without absolute-value masking.
Four targeted tests include wrong split despite exact total balance, reversal,
missing/nonfinite data and duplicate steps. Actual200native samples pass with
an explicit1e-10boundary-algebra target. Pressure and engineering acceptance
always remain false. Caller must separately bind patch names, steps and units.


## Analytic laminar pressure and units

The existing synthetic channel benchmark parameters are reused in a native
OpenFOAM planar Poiseuille case: L1m,H0.1m,Umean1m/s,nu0.01m2/s,48x32cells and
explicit0.01mempty-direction depth. These are benchmark values, not project air
properties. This is a native blockMesh case, not byte-identical to the SU2 mesh.
The inlet parabola is sampled at actual native face centres. Mesh OK and1000
steady steps complete with no turbulence model. The1%relative target is written
before execution. Actual1536cell centres are independently reconstructed from
owner/neighbour face vertices;896cells within0.2<x<0.8m are compared.

The analytic solution u=6Umean(y/H)(1-y/H) gives
 d(p/rho)/dx=-12nuUmean/H^2=-12m/s2.
Native slope is-11.98246208, relative error0.14615%; native velocity-profile L2
error is0.05954%. Both pass the declared1%synthetic check. Native saved p has
dimensions[0 2 -2 0 0 0 0], so it is kinematic pressure, not Pa. Multiplying by
an explicit test density1.2kg/m3 gives-14.37895450Pa/m against-14.4Pa/m.
This checks laminar pressure handling and conversion only; turbulent fittings,
actual branch pressure, station correspondence and project acceptance remain
unverified. [Executed analytic receipt](evidence/openfoam-analytic-channel.json).
