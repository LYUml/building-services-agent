# Native fitting revisions from the recentered scenario

The actual compensated Connection_Layout now supplies fresh source node frames
and sizes for six affected tee/main-transition groups. Existing source-node
compiler, reduced-tee author, station BREP transition author, native cap reader,
Manifold material checks and bounded table engine execute without modification.
No new solver, dependency or staged fitting joint is introduced.

Six reduced tees and six main transitions are rebuilt, preserving inherited
nominal-size/internal-size, gauge, reference elevation and construction-policy
assumptions. The three enlarged trunk sections naturally create two equal-angle
pyramidal contractions and one one-plane contraction. This replaces the need
to introduce speculative staged transitions merely to match source table families.

Independent native cap reconstruction matches all six tee/main-transition joints,
six external main sections and six branch sections; local material overlap is
zero. Three bounded source-query coefficients and separate Decimal calculations
agree. Conditional maximum/minimum local dynamic contributions are:

| Source section | Maximum Pa | Given40%minimum Pa |
|---|---:|---:|
| D-20 | 0.655427 | 0.104868 |
| D-13 | 0.810387 | 0.129662 |
| D-06 | 0.650845 | 0.104135 |

These use the actual owned inlet reference, source-prescribed flow and the
existing tentative round-adapted contraction data. Family matching is necessary
but not a manufacturer/product or installed-flow acceptance. Floating angles
are not snapped; reviewed15/30/45degree one-plane support is retained.

This is an executed local rebase, not an integrated network. Whole-network links,
straight trimming/resizing, shifted elbows, all outlet frames, raw clash policy,
complete pressure and matching native CAD still need updating and verification.
The existing network therefore remains30conditional fitting paths/33numerical
gaps. No whole-network pressure saving or gap reduction is claimed yet.

Private sources/native cases/review are under
`07_Agent_Work/runs/recentered-local-fittings`. Separate clean derived IFCs are
delivered under Connection_Layout/Fitting_Study for review, not installation.
