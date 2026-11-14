# Terminal pressure interpolation diagnostic

A separate source-calibrated study now tests whether the low-flow native versus
linear-catalogue discrepancy is compatible with a quadratic pressure curve.
No production pressure method or original design is replaced.

Nine visually reviewed archival Krueger B1-12 total-pressure IP rows admit a
common coefficient in P=kQ² within their printed0.001inch-water resolution.
The midpoint of the feasible coefficient interval is selected using the catalogue
alone. Existing native112/280/300CFM PDFs, independently verified through the
user K-Select MCP, are held out from calibration. All three agree with assumed
nearest0.01inch-water native display precision. Source and native rounding rules
are explicit diagnostic assumptions, not measurement error estimates.

This is a possible explanation of the earlier discrepancy, not proof of the
software's internal equation. The official [Krueger engineering guide](https://www.krueger-hvac.com/file/9261/GRD_Engineering.pdf)
defines outlet total pressure and its upstream measurement context. It does not
establish that this fitted constant applies to the actual installation. General
[fluids pressure conversion](https://fluids.readthedocs.io/fluids.core.html#fluids.core.dP_from_K)
also makes the constant-coefficient/density/geometry assumptions explicit through
the velocity-squared relationship; no rectangular-to-round substitution is made.

All80 source terminal maximum/minimum pairs are evaluated inside the printed
flow domain. SD-01 minimum pressure is3.653756Pa in this diagnostic versus
3.990838Pa from existing linear interpolation; maximum is22.835973Pa versus
22.780658Pa. Across160cases the linear-minus-diagnostic difference ranges from
-0.055315to0.348420Pa. No lower complete fan duty or energy saving is inferred.
Existing static pressure, acoustics, throw, ADPI and fitting gaps are unchanged.

Independent artifact review reconciles960HTMLcells, all160sourceflows and
all80given40percent-flow pressure ratios. Input/method/source hashes are rechecked.
Existing pinned fluids1.3.1, MCPclient1.30.0 and external toolkit0.1.1 are reused;
no dependency or solver is added. Upstream MCP verification, catalogue parsing
and bounded interpolation remain in their existing engines.

The inferred coefficient interval describes source rounding only. Manufacturing,
Reynolds, laboratory uncertainty, installation, adjacent joints and source/software
edition equivalence are unverified. It is not an experimental confidence interval.
Complete fan duty and engineering acceptance remain false. The current network
still has30conditional fitting paths and33numerical gaps.

Course outputs: Terminal Pressure Interpolation Review.html and
Terminal_Pressure_Interpolation_Check.json. Full private records are under
`07_Agent_Work/runs/terminal-pressure-source-envelope-reviewed`; the earlier
unreviewed study remains historical. Next work should advance load-basis and
selected-scenario coordination rather than repeatedly fitting this small pressure
difference while major component/installation gaps remain.
