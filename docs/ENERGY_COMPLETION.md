# Native EnergyPlus completion diagnosis

Both design-day and annual wrappers now save `completion.json` before accepting an engine result. This is a separate completion check: it does not replace calendar coverage, numerical balances, model applicability or engineering acceptance.

The classifier combines the actual subprocess return code, stdout success marker, native eplusout.end warning/severe counts, severe/fatal error text, SQL simulation version and both native completion flags. Required files and the single SQL simulation row are checked. Missing/unreadable SQL cannot prove completion. Every available native source file is hashed before/after read-only inspection; SQL flags and engine binaries are never edited.

## Source-backed 25.2 limitation

The inspected official Windows x64 EnergyPlus 25.2.0-cf7368216c executable has SHA256 `51715987663666eaff1c8d3bd6ac2d7fe0486d8bc93673eea87c6912a79103f0`, independently matched to the already checksum-verified official release archive. The release tag resolves to source commit `cf7368216c73c43181e057fa33b479c4e0c86df0`.

In that source, normal [wrapUpEnergyPlus](https://github.com/NatLabRockies/EnergyPlus/blob/cf7368216c73c43181e057fa33b479c4e0c86df0/src/EnergyPlus/api/EnergyPlusPgm.cc) releases the SQLite object before calling EndEnergyPlus. The success-flag update in [EndEnergyPlus](https://github.com/NatLabRockies/EnergyPlus/blob/cf7368216c73c43181e057fa33b479c4e0c86df0/src/EnergyPlus/UtilityRoutines.cc) is guarded by that object's continued existence. The [SQL initializer](https://github.com/NatLabRockies/EnergyPlus/blob/cf7368216c73c43181e057fa33b479c4e0c86df0/src/EnergyPlus/SQLiteProcedures.cc) starts both fields as text FALSE. This ordering explains the observed default flags in a normally completed run: it is a source-based inference tied to verified executable bytes and native reproduction, not instrumented instruction tracing.

The audit recognizes this limitation only for that exact build/version and executable hash, and only when every other native completion check succeeds. It reports `verified_with_known_unwritten_sql_flags`, preserves the raw FALSE/FALSE values and explicitly records that native SQL success flags are not true. Unknown binaries/versions do not receive that exception. Actual failures, nonzero exits, severe/fatal diagnostics, bad end reports or explicit SQL failure flags cannot be cleared by the exception.

| Evidence | Result |
|---|---|
| All native checks succeed; SQL true/true | verified |
| All native checks succeed; initial false/false on the exact inspected executable | verified_with_known_unwritten_sql_flags |
| Healthy markers but unknown initial flags/binary/version, malformed flags or missing SQL | needs_review; not verified |
| Failed process/end/error evidence or SQL true/false | failed |

The normal reproduction retained text FALSE/FALSE with zero exit, successful end/log, no severe errors and full annual data. A controlled nonexistent-construction case on the same unchanged executable returned a fatal failure and native SQL integer 1/0; the classifier retained failure. [Source/binary/control-run evidence](evidence/energy-completion/README.md) records the hashes and unchanged native files. Earlier annual evidence is preserved as historical evidence of the initially unexplained observation.

## Path and scope checks

SQLite read-only URIs use encoded absolute file URLs. A reproduced unescaped `#` directory name truncated the old URI and discarded its query, allowing an unintended empty prefix file. Tests now use spaces/`#` paths for completion, design-day and annual SQL readers and check that no sibling file appears. This fixes the observed path issue without changing query/accounting formulas.

The wrappers obtain the actual return code and executable hash themselves. The Python `bsa.energy_completion.inspect(folder, returncode, engine_version, engine_sha256)` API expects those facts from its caller. Its records are source/byte-consistency evidence, not authenticated execution logs or a signed certification. Real model/weather/product/HVAC applicability, period/numerical QA and professional acceptance remain separate gates.
