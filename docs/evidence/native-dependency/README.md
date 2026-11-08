# Native dependency dispatch

The existing shared-lighting-plan.json was executed without Radiance and with an explicit dummy AutoCAD path. Conversion was mocked to raise if reached. Before the fix, conversion was called and the native task failed; afterward it is not called and stays pending with the producer identity/status. The manual independent review is still visited.

Eight workflow cases pass. Additional mocked false/true producer controls verify blocked failure and allowed successful dispatch, including the registered shared electrical DXF path. This does not verify actual native drawing geometry. Initial new pass-path test attempts failed due to a Windows short versus resolved temporary-path assertion; the fixture now resolves paths and keeps its temporary runs within this repository. No engine result was fabricated.
