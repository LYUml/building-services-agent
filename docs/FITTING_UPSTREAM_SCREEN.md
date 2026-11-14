# Remaining fitting-gap upstream screen

Inspected 2026-11-14 against the saved reduced-branch network, currently with
30 conditional paths and 33 numerical gaps. No new coefficient is adopted.

## Executed closest candidate

[python-hvac source](https://github.com/TomLXXVI/python-hvac/blob/94247560a667905bfbf67e45a58965a58254fce8/hvac/fluid_flow/fittings/duct/smacna.py),
MIT, commit `94247560a667905bfbf67e45a58965a58254fce8`: literal AST extraction
of `DivergingJunctionA11P`, with inherited A11N axes, exact previously pinned
source/license hashes and existing bounded SciPy lookup executes on 13 actual
revised branch queries. Missing sentinel 9999.9 is masked, never used as K.
One previously supported point matches; 12 still need unpublished cells.
Newly supported paths: zero. Data-only execution, not upstream package execution;
the class still calls removed interp2d. Previously screened contraction A9B does
not justify collapsing unequal native wall angles to their maximum.

## Other inspected candidates

- [hvac-fitting-loss](https://github.com/JeremySimonneau/hvac-fitting-loss):
  prior pinned hvac-pressure0.1.1 execution remains applicable. Current source
  again confirms out-of-bounds clamping; rounded-branch and one-plane metadata
  do not match all present sharp junctions/unequal-angle transitions.
- [pyduct source](https://github.com/TunaLobster/pyduct/blob/d6da49771f286637f8e18c4d52e6b52276642964/pyduct.py),
  MIT, commit `d6da49771f286637f8e18c4d52e6b52276642964`: circular-diameter
  input and SD5-10 conical tapered-branch correlation, not this rectangular
  sharp-tee family. Source inspection only, not executed or integrated.
- [Revit_Extensions coefficient injector](https://github.com/Jebraouilyass/Revit_Extensions/blob/6770f1f583e044b2caa7f9c7f318b07928e4b72d/MEPTools.extension/MEPTools.tab/Calculations.panel/CalcCoefficient.pushbutton/script.py),
  commit `6770f1f583e044b2caa7f9c7f318b07928e4b72d`: actual source is an
  angle-only elbow coefficient injector, not a general fitting database.
  Repository metadata has no license. No installation, execution or reuse.
- [RevitMEPTransparent fitting server](https://github.com/DaltonGOO/RevitMEPTransparent/blob/0af8102579d0ffc1f732e19583ae2966608ceced/src/RevitMEPTransparent/Servers/Duct/DuctFittingPressureDropServer.cs),
  MIT, commit `0af8102579d0ffc1f732e19583ae2966608ceced`: source marks entities
  valid while K-factor calculation remains TODO. Straight friction is a
  different capability already covered here. Not executed or integrated.

## Credible remaining routes

[ASHRAE DFDB](https://www.ashrae.org/technical-resources/bookstore/duct-fitting-database)
is a commercial cloud subscription with more than200fitting types and geometry/
flow queries. Its coverage is a candidate, not proof it handles these exact
missing geometries. No subscription, account or licensed data was accessed.
Confirm actual fitting coverage and permitted use before purchase/adoption;
an open-source wrapper does not itself license third-party data.

[OpenFOAM](https://github.com/OpenFOAM/OpenFOAM-13) and
[IIT Bombay FOSSEE's rectangular T-junction study](https://cfd.fossee.in/research-migration-project/download/project-file/60)
provide existing CFD engines/prior workflows. The latter studies merging flow
at Re7500 and velocity profiles, not validated current diverging pressure losses.
They are not executed integrations here. Geometry, pressure stations, mesh and
experimental validation remain necessary. Network solvers requiring user-entered
K values cannot independently supply missing K.

Decision: retain verified engines and explicit missing values. Pause batch
expansion of the staged geometry idea until a defensible fitting/interaction
source is identified. The single native two-stage candidate remains separate.
Prioritize source/manufacturer coverage for actual construction rather than
multiplying individually tabulated components with unknown combined loss.
No purchase or CFD scope decision is made on the user's behalf.

Private execution: `07_Agent_Work/runs/upstream-sparse-tee-screen/review.json`.
Public evidence contains aggregates only; protected grids/source caches stay
in the selected private project workspace.
