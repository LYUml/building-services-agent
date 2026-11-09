# Synthetic three-phase network basis

Original software integration fixture; no measured building, product ratings or regulatory limits.

Supply: 400 V line-line, 50 Hz, 1.0 pu, 0 degree; sequence source inputs s_sc_max_mva=100, rx_max=0.1, x0x_max=1, r0x0_max=0.1. These are assumed upstream solver parameters, not an installation fault study.

All lines: r1=0.2, x1=0.08, r0=0.6, x0=0.24 ohm/km. Zero shunt capacitance; negative sequence equals positive sequence. Source to DB-A is 40 m; DB-A to load-B is 25 m. Each line has a synthetic 100 A study target, not a verified cable rating.

Wye constant-power loads, phase A/B/C: at DB-A electrical active power 5/4/3 kW and reactive power 1/0.5/-0.2 kvar; at load-B electrical active power 1/2/3 kW and reactive power 0.1/0.2/0.3 kvar. Negative reactive demand is an explicitly capacitive test component, not generation of active power.

All bus phase-voltage study targets: 0.95 through 1.05 pu. These numerical targets are synthetic, not Hong Kong limits. No physical neutral model, harmonic current, protection selection or design acceptance is provided.
