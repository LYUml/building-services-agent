# Synthetic IFC topology acceptance example

Use project.json to create an IFC4 office space with the given distribution board and luminaire envelopes. Preserve their explicit electrical system membership, equipment IDs, electrical input and source descriptions. Create the given logical source-to-sink port relationship; do not claim it is a physically routed cable.

Use ventilation.json to create the synthetic fan, straight duct envelope and air terminal in the plant-room space. Preserve the supply-air system and two explicit directed connections. Reopen and check geometry, containment, topology and IFC4 schema. Do not infer calculated duct sizing or operating performance.
