# Source-based rectangle-to-round transitions

Twenty project tapers are changed from300mm to L=D (304.8 or355.6mm), with50mm end collars retained. Eight candidate equipment inlet positions move. Source originals and previous designs are preserved.

The native metre-IFC reader derives W,H,D,taper length and Reynolds/area parameters from supported analytic CSG and owned ports. It rejects missing/nonmetre units, invalid surfaces and displaced ports. Seven targeted controls pass. This is a thin project-tested reader, not a registered general mixed-network producer.

The official 2021 Online Supplemental Material Accompanying Principles of HVAC,9th Edition, Fitting4-6 printed21/22 right-hand contraction table (Idelchik et al1986 Diagram5-26) uses Re/10000,L/D and B=(W/H)(Ao/A1)^2. Reference velocity is the circular outlet. Original40queries are outside L/D support; revised40queries are bounded and agree with independent Decimal interpolation. No extrapolation or raw proprietary grid is published. Physical equivalence and whole-assembly/collar losses remain unverified.

Actual129body/277port/128link IFC retains33requirement IDs and both source flows. All128native material interfaces pass. Both pressure cases have65straight spans and83fitting paths:51conditional values and32numerical gaps. No full pressure, fan duty or critical path is accepted. Zero rigid-network solid intersections and128unwaived contact-clearance findings remain. Separate149body network/casing check finds zero intersections;60nonphysical reservations are excluded.

Actual AutoCAD save/reopen verifies23744entities; inspected A4 PDF is1:200 with10m reference measuring49.995667mm. Twenty labels and200coordinate cells reconcile;280pressure report cells reconcile. Casings are in a separate IFC. Existing flex/discharge scenario is not adopted as installed geometry.

Reuse: existing pinned CadQuery2.6.1/OCP7.8.1.1.post1, IfcOpenShell and bounded SciPy interpolation execute. The previously surveyed MIT python-hvac commit94247560a667905bfbf67e45a58965a58254fce8 ConvergingTransitionA9C was inspected but not adopted: its Reynolds-only correlation does not implement this three-axis table. No new solver or dependency is introduced.

Source: https://xp20.ashrae.org/SupplementalFiles/PHVAC9/Fitting_Loss_Coefficients.pdf
Evidence: [derived checks](evidence/sourced-inlet-network.json).
Course delivery:03_Design_Drawings/Connection_Layout/Source_Based_Inlet_Design and05_Calculations/Connection_Layout/Sourced*. Full equipment/discharge/plenum/flex, actual load/ADPI, installation and final submission remain incomplete.
