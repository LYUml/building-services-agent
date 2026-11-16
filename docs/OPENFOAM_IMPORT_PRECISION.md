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


## Actual first-family startup, rejected pressure

The existing optimized first-family813620cell mesh executes a bounded10step
native kOmegaSST startup. Inheriting old uniform inlet speed over the native
inlet area changes Q by0.0052923%relative to source design; this first trial is
retained and not adopted. A separate trial directly binds flowRateInletVelocity
and all four flowRateOutletVelocity targets to the current family-review VAV-01
maximum flow0.5756751425686069m3/s and its four source fractions. Density1.2,
mu1.81e-5 and inletI0.05/viscosity-ratio10 are inherited explicit assumptions.
The previous10field is numerical initialization only. Bounded first-order
upwind replaces higher-order convection for diagnosis. Ten steps preserve all
five signed source targets within1.221e-14relative; negative-k bounding events
fall from5to0. This is neither a200step window nor pressure convergence.

A single additional step verifies native pressure output. The packaged pressure
function creates Pt in Pa, and surfaceFieldValue average with weightField phi
computes signed flux-weighted averages (not areaAverage or an unsupported
weightedAverage operation). Independent saved11U/p/phi reconstruction checks
all24556port faces; zeroGradient p comes from native owner-cell internal values
because the saved boundary does not serialize values. Native Pt agrees with
rho*(p+|U|^2/2) within7.276e-12Pa and averages within7.276e-12Pa.

Crucially outlet_1 has maximum local speed357.880m/s, while other ports are
approximately3.6--4.3m/s. The unconverged pressure field is REJECTED; successful
flow control and exact observer algebra do not make it usable. No pressure
component is filled in the project ledger. Next: localize this spike before
further iteration. Native smooth low-Re nut0/k0/omegaWallFunction equivalence to
previous SU2 settings, SST applicability and three mesh-quality checks all remain
unverified. [Actual startup receipt](evidence/openfoam-actual-plenum-startup.json).


## Source-preserving history adapter

bsa.openfoam_history reads pinned two-column surfaceFieldValue sum(phi) and
average(Pt) records for steady deltaT1cases. It requires exact column headers,
finite values, consecutive integer times and complete newline-terminated rows.
It rejects duplicate restart times, missing rows and misaligned patch histories;
it does not silently merge or trim segments. Caller binds phi=m3/s, verified
Pt=Pa, actual weighting and an explicit source density. Conversion uses
inward-positive mass=-rho*phi and leaves Pt unchanged, then reuses the existing
cfd_convergence numerical assessor without changing its thresholds. Three tests
cover sign/density/pressure handling, incomplete/nonfinite/duplicate rows and
cross-channel misalignment. Actual frozen first-family startup0segment replay
passes flow/mass but correctly FAILS pressure stability across20samples. This
is deliberately not a200step assessment. [Executed adapter receipt](evidence/openfoam-history-adapter.json).

Cold-start source-flow diagnostics reduce global peak speed205.290at saved10
to39.151at20,18.386at30 and7.031at50. The60step run completes normally but its
latest saved field is50, because native time indices inherited an offset from
copied initialization metadata. A bounded200step continuation therefore resumes
from actual saved50, retaining old51..60observations separately instead of
counting overlap twice. This live continuation has no acceptance result yet.


## First actual complete numerical window

The bounded continuation finishes250normally and writes the complete250field.
The adapter uses only native postProcessing50times51..250 (200consecutive
samples), without stitching the overlapping older51..60segment. All signed
source flows and global conservation pass. All four total-pressure differences
are positive, but their range/mean is39.3%--59.6%, exceeding the unchanged0.5%
numerical target. The complete window FAILS; no design pressure is adopted.

Final250global peak speed is6.697m/s with no negative-k bounding events. Last50
pressure ranges are0.941%,1.354%,1.449%,0.394% for outlets0..3: substantial
settling versus the full early window, but not a200step acceptance. This supports
a further bounded source-identical continuation with only equation relaxation
0.5to0.7. It starts from actual saved250, caps at650, expects fields430/650 and
will assess only451..650. Source physics, grid, exact flow targets and numerical
acceptance thresholds are unchanged. Mesh, model, higher-order and physical
validation remain open. [Executed failed window](evidence/openfoam-plenum-window.json).
