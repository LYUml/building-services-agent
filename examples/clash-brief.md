# Synthetic IFC coordination checks

Generate the supplied circular network's selected IFC revision using the common source inputs and catalogue, preserving original hashes, endpoints and project object identities. Keep product, material, operating-point and engineering acceptance gates pending.

Check the saved selected IFC against the supplied all-element geometry policy. Use 50 mm minimum clearance, 0.1 mm intersection/contact tolerances and a 1e-10 m3 overlap-volume threshold, with the stated Boolean search budget. Preserve intersections, failed clearances and unverified/missing geometry evidence. Only the explicitly supplied coincident connected-port contacts may receive the sourced witness-region exception; never use it to waive a solid overlap. Other-zone clearance on contact-exempt pairs and BIM-viewer review remain pending. These are synthetic QA settings, not regulation clauses or installed-equipment clearances.
