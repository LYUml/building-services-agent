# Actual-endpoint staged transition candidate

The project now has a separate native two-stage replacement candidate for one
unequal-angle contraction. It reuses the existing pinned IfcOpenShell station
BREP transition author, Manifold material checks and bounded source-table reader.
No new solver or dependency was introduced.

Inherited clear sections are 600 x 400 mm to 500 x 350 mm. A derived 550 x 350 mm
intermediate section separates an equal-angle pyramidal contraction from a
one-plane contraction. The straight-end allowance is redistributed into four
25 mm ends; that is an explicit construction assumption, not a product detail.
Both external frames and the original total length 0.28660254037844385 m remain.

Both saved IFCs pass schema/native material checks. Independent material-cap
reconstruction matches both original external ends and the new internal joint;
the two saved material solids have zero intersection volume. Actual included
angles pass their respective source-family screens. Bounded conditional queries
and separate Decimal arithmetic agree. Native floating angles are not snapped:
the one-plane study uses the reviewed contraction 15/30-degree support, keeping
the original publication's duplicate 30 headers unchanged.

This adds one joint and short intermediate straight portions. Published
contraction data are tentative round-adapted values. Adjacent-fitting interaction,
joint construction, loss stations/friction and fabrication viability remain
unverified. The two source values must not be treated as complete combined loss.
No pressure improvement or reduction in the current network's 33 gaps is claimed.

The candidate remains separate from the saved network and delivered CAD scenario.
Network integration, full-neighbour clash review, native DWG/plot review and
physical acceptance are pending. Project evidence is under
`07_Agent_Work/runs/staged-transition-candidate-reviewed`; the first trial is
retained with its genuine out-of-domain query rather than a rounded angle.
