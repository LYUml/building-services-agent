# Native diffuser-export reconciliation

The existing native K-Select SD-01 maximum-flow export and performance table were
rendered and visually inspected, alongside the original Krueger2012 B1-12 page.
The calculation reuses the existing fluids1.3.1-backed terminal_performance
adapter, with independent Decimal pressure interpolation. No K-Select MCP or new
selection engine is built here, and the native software was not rerun this turn.

SD-01 inherited design flow132.207946L/s equals280.132774CFM; the export280CFM
agrees at integer display precision. Catalogue Pt22.780658Pa and Ps12.844740Pa
remain separate. Native0.09inch-water agrees numerically with Pt at the export's
two-decimal precision, not Ps. The generic export label alone does not establish
the software pressure definition. Existing historical80-terminal/160-case
catalogue results are not claimed as newly executed native software selections.

An actual unit-label conflict is present on the same native page: the table
reports14feet while the specified-airflow summary reports14.0metres. The former
converts to4.2672m and agrees with archival throw at published display precision;
the latter is rejected as a usable metric input. The original PDF stays intact.
Do not silently correct its label or import the summary as14m.

At the nearby archival279CFM point, exported NC20 agrees, but octave band5 differs
by1dB. No acoustic tolerance or exact acoustic equivalence is established.
Minimum-flow native export and numerical ADPI remain pending. Actual installation,
room load, physical applicability and full fan duty are not accepted.

Derived course outputs: Diffuser Export Review.html and KSelect_Export_Check.json.
Private originals, actual rendered pages, source hashes and audit script remain
under the selected project workspace. Public evidence includes the observed
unit conflict, scoped numerical comparisons and unresolved checks only.
