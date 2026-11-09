# Native Revit adapter (development)

Original source; uses Autodesk's installed proprietary RevitAPI/RevitAPIUI references without redistributing them. API usage follows the official [Pipe.Create reference](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/9550265f-5760-3c28-d023-d0373285855b.htm); compilation checks against local 2027 binaries. Upstream bridge and plumbing-project research attribution is in ../../docs/REVIT_MOOSAS_DIRECTION.md; no upstream implementation copied.

The locally installed Microsoft .NET SDK 10.0.403 archive was SHA512-checked against official release metadata. It resides only in ignored tools, with its bundled licences/notices retained. From this directory:

```powershell
../../tools/dotnet-sdk-10.0.403/dotnet.exe build Bsa.Revit.csproj --configuration Release --nologo
```

Final observed build: zero warnings/errors. The initial build had desktop-reference conflicts; explicit WPF/WindowsForms framework references resolved them. The intermediate missing System.IO import was corrected. Evidence and source/binary hashes: ../../docs/evidence/moosas-review/revit-native-build.json.

`NativePipes.Create(UIApplication, PipeRequest)` must be called from a valid Revit API context on an explicitly selected test model. It checks active saved document identity, rejects existing edits/transactions, uses supplied type/system/level UniqueIds and metre-valued coordinates/diameter, creates a native Pipe and verifies dimensions/endpoints/two connectors. Any Revit failure message rolls back the transaction rather than being waived. No save/export or add-in registration is performed. The returned object explicitly leaves saved, system-connectivity and design acceptance false.

This is a compiled library, not an installed MCP/add-in or verified modeling workflow. Required next evidence: host invocation, positive and invalid-type/diameter controls, rollback/readback, source-bound saved reopening, actual joined pipes/fittings, sheets and visual review. The current method creates only one isolated pipe; it does not solve routing, select products, prove physical connections or establish Hong Kong compliance. Do not use it on the finished coursework or infer suitability from compilation.

## Read-only host entry point

The current C# inventory also collects native pipe-fitting family instances and reports missing connector managers explicitly. Each connector retains its domain/type, physical `IsConnected` flag (null for logical connectors), external references, reciprocal-reference evidence and endpoint separation in metres. `IsConnectedTo` is recorded as an API relation rather than promoted to physical-system acceptance. Logical connector origins and distances remain null instead of making unsupported physical queries. This follows the installed Revit 2027 `RevitAPI.xml` contracts for `Connector.IsConnected` and `Connector.IsConnectedTo`.

The extended source compiles with zero warnings/errors (`../../docs/evidence/moosas-review/revit-connectivity-build.json`). No host execution has occurred: runtime handling of connector varieties, joined/unjoined controls, fitting coverage, saved reopening and full system traversal remain pending. The report explicitly retains `connected_system_verified = false`. Accessories, equipment, flexible pipes and linked models are not included; a missing item must not be interpreted as an open network endpoint. The separate Python inventory has not yet acquired these additional fields.

`InventoryCommand` implements IExternalCommand with TransactionMode.ReadOnly. Its Execute entry opens a request-file picker; `Run(UIApplication, requestPath)` is also callable from a valid API context. The request contains absolute `DocumentPath` and `ReportPath`; the JSON and both paths must reside under this repository. It rejects family/unsaved/mismatched documents, checks model and request bytes before/after collection, and creates a new JSON report with model/request/assembly hashes. It reads native pipe/type/system/level identities and connector references. Logical references, linked models and physical connectivity remain outside acceptance. It opens no other documents or transactions.

From the repository root, prepare a local manifest and request:

```powershell
./scripts/prepare_revit_addin.ps1 -Model runs/revit-native-v1/test.rvt -Out runs/revit-addin-v1
```

This command only prepares files; it does not register the add-in, restart Revit, or claim that the RVT exists. `InventoryCommand` compiled with zero warnings/errors against the local API. Its current build evidence is ../../docs/evidence/moosas-review/revit-inventory-build.json; the earlier native-pipe evidence identifies an older assembly. Manifest XML was generated and read back. Actual registration, loading, invocation and readback are still pending desktop availability. Generated manifests reference the current build output, so regenerate/review hashes after rebuilding. The Python/Dynamo route remains an alternative pending path, not another verified implementation.

Host integration follows Autodesk's [IExternalCommand reference](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/ad99887e-db50-bf8f-e4e6-2fb86082b5fb.htm) and [transaction-mode contract](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/84254a1f-7bba-885a-ce65-e68fc238fddb.htm).
