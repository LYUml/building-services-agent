# Developed-inlet bend check

The original pinned upstream bend has now run with the numerically verified developed inlet. SU2 8.6.0 exits normally at iteration 498 with all six logRMS residuals <= -10. Existing `bsa.cfd_convergence` checks the complete last 200 iterations (299–498): signed inlet/outlet flow and mass targets pass, and total-pressure difference is stable. Mean complete-domain difference is 21.57356824 Pa with relative range 3.6538e-5. This includes the benchmark straight sections, not an isolated bend coefficient or project loss.

Existing `bsa.cfd_native_probe` binds all 75396 saved mesh points and extracts the same 40 native diameter nodes without interpolation. A separate conditional comparison interpolates these 40 values to all 27 pinned upstream CSV abscissae, without extrapolation. Assumed coordinates remain r/D=(z-0.208)/0.104 and velocity=global Ux/8.7. The original experimental full text, normalization and measurement uncertainty remain unverified.

Conditional normalized RMSE is 0.17817964 for the developed inlet, versus 0.17774048 for the supplied inlet and 0.22653723 for the uniform inlet. The developed and supplied curves nearly coincide; the inner-side discrepancy remains. The tested inlet-development change therefore did not resolve this discrepancy under the stated assumptions. These cases have different integrated flows, so this is not a fixed-flow shape-only sensitivity. No statistical agreement threshold or accepted physical error is invented.

![Conditional comparison](evidence/developed-bend-comparison.png)

[Executed evidence](evidence/developed-bend-check.json) pins the native field, mesh, probe method, numerical-window method and experimental CSV. The actual rendered figure was inspected. Raw mesh/field/profile and private run records remain local.

Reuse: SU2 commit 7048fd35f56d4bf52e586429d6746a36a10255f8 and official Tutorials commit ce41729be812da70f06bea0fd1a97a6ce4da14aa, LGPL-2.1; existing native probe and convergence adapters; NumPy 2.5.4 and Matplotlib 3.11.2. The experimental CSV is attributed to the pinned Sudo bend tutorial. Original experiment: Sudo, Sumida and Hibara (1998), DOI https://doi.org/10.1007/s003480050206 . No new engine, dependency or MCP is added.

Numerical convergence does not establish experimental agreement, turbulence validity, mesh independence or applicability to rough installed project ducts and lined plenums. The next physical verification must distinguish source-normalization, mesh and model effects rather than repeat inlet development. All 80 plenum and four compound-main project numerical losses per flow case remain missing; full fan duty and course delivery acceptance remain pending.
