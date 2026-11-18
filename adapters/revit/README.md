# Native Revit adapter (development)

A fresh built-in Revit2027.3 test-copy opening now executes, preserving both RVT
files and39warnings/four unresolved links. Export menu navigation remains blocked
by the observed UI-control failure, with no IFC produced. This is separate from
the original unsigned-adapter policy block; no adapter was retried. See
../../docs/REVIT_BUILTIN_INTERCHANGE.md for actual scope and remaining checks.

See [signing investigation](../../docs/REVIT_SIGNING.md) for provider eligibility, current gaps and required post-signing native verification. Build metadata evidence is [revit-signing-metadata-build.json](../../docs/evidence/moosas-review/revit-signing-metadata-build.json); this newer unsigned DLL does not replace the historical hash from the blocked host attempt.

Current live status: Revit discovered and registered the inventory command in-session, and the user-authorized Load Once action was accepted. Actual invocation then triggered Windows Application Control: Code Integrity events 3077/3033 identify Bsa.Revit.dll as failing Enterprise signing requirements. Authenticode reports NotSigned. No inventory was produced. Evidence: ../../docs/evidence/moosas-review/revit-native-policy-block.json. Compilation, manifest parsing and button registration must not be reported as executable native integration. Do not retry via another loader, move the DLL to evade policy, or change security settings. A supported signing/deployment route requires the applicable policy's approved trust basis; adding a self-signed certificate alone does not establish it.

Original source; uses Autodesk's installed proprietary RevitAPI/RevitAPIUI references without redistributing them. API usage follows the official [Pipe.Create reference](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/9550265f-5760-3c28-d023-d0373285855b.htm); compilation checks against local 2027 binaries. Upstream bridge and plumbing-project research attribution is in ../../docs/REVIT_MOOSAS_DIRECTION.md; no upstream implementation copied.

The locally installed Microsoft .NET SDK 10.0.403 archive was SHA512-checked against official release metadata. It resides only in ignored tools, with its bundled licences/notices retained. From this directory:

```powershell
../../tools/dotnet-sdk-10.0.403/dotnet.exe build Bsa.Revit.csproj --configuration Release --nologo
```

To compile just the DB operations against the installed Revit API, use a
separate artifacts directory from the desktop build:

```powershell
../../tools/dotnet-sdk-10.0.403/dotnet.exe build Bsa.Revit.csproj -c Release -warnaserror -p:DatabaseOnly=true --artifacts-path ../../runs/revit-db-build
```

The resulting `Bsa.Revit.Database.dll` was built against Revit 2027.3.
Its assembly metadata references `RevitAPI` and has no `RevitAPIUI`
reference. The .NET Windows Desktop build references resolve dependencies
of the installed Autodesk API.

Use `-p:Automation=true` in place of `-p:DatabaseOnly=true` to compile
the read-only Automation inventory entry point. It uses Autodesk's pinned
[Design Automation Bridge 2027.0.0](https://www.nuget.org/packages/Autodesk.Forge.DesignAutomation.Revit/2027.0.0).
NuGet retains the package's Autodesk licence. The build uses the package for
compilation and leaves its runtime assembly to the host.
The entry point takes the engine-opened `input.rvt` and an
`inventory-request.json` containing `SavedRvtSha256`. It checks the model
hash and writes a fresh `inventory.json`. A local build against Revit 2027.3
passed. From the repository root, package the built DLL locally:

```powershell
python scripts/prepare_revit_automation_bundle.py --assembly runs/<build>/bin/Bsa.Revit/release/Bsa.Revit.Automation.dll --out runs/<new-bundle>
```

The ZIP contains the adapter DLL and its two XML manifests. The receipt
pins the ZIP and DLL hashes. The local trial also checked the entry-point
type and absence of a `RevitAPIUI` assembly reference. [Autodesk AppBundle layout](https://get-started.aps.autodesk.com/tutorials/design-automation/prepare-plugin/)

Add `--engine <catalogue-id> --bundle-id <owner.bundle+alias>` to stage
the inventory Activity JSON. The command line and three required transfer
parameters follow the [Autodesk Activity tutorial](https://get-started.aps.autodesk.com/tutorials/design-automation/define-activity/).
The local preparation receipt pins the Activity bytes. Engine and alias
availability must be checked with authenticated APS before deployment.
With the optional `revit-metadata` extra, pass `--inspect-model` together with
`--model` to pin the saved release and worksharing flags before staging.
This preflight rejects a newer release. Pipe creation requires a model saved
in Revit 2027 and rejects known workshared or single-user cloud inputs. Upgrade
an older model on a separate copy before preparing its pipe request. The native
creation entry point also checks the saved release before writing. `--verify-stage` rechecks the
same metadata when present. Unknown flags and native opening remain unresolved.
Add `--check-engine` to check the selected engine in the US East catalogue
before writing the staging directory. The command reads the application
token from `APS_ACCESS_TOKEN` and records the returned engine ID and build
version. [Autodesk engine lookup](https://aps.autodesk.com/en/docs/design-automation/v3/reference/http/engines-id-GET)
Actual work-item execution remains pending.

## Desktop smoke test with Revit.TestRunner

`adapters/revit-tests/Bsa.Revit.NativeTests.csproj` builds an NUnit fixture
against the desktop adapter using .NET 10 and a locked NUnit dependency.
Build with `-p:RestoreLockedMode=true`. On a dedicated, authorized Revit 2027
test host, run `CapturesSyntheticPipeInventory` first with the absolute
test RVT in `BSA_REVIT_TEST_RVT`. It reports the copied model path and
native inventory. Run `bsa revit-file-metadata <fixture.rvt> --engine-release 2027`
before scheduling the host run. Both fixtures verify the copied bytes and use
Revit BasicFileInfo to require a standalone model saved in the host release
before opening it. Select their temporary directory as `BSA_PROJECT_ROOT`
when preparing the request with `bsa revit-prepare-pipe`. Use explicit
endpoints, diameter and source basis and select type, system and level IDs
from that inventory.

For `CreatesAndReopensOnePipe`, set `BSA_REVIT_TEST_REQUEST` for the Revit process to the absolute
path of a prepared synthetic pipe request beside its source RVT. The test
copies the RVT into a fresh temporary directory. A rollback control creates
a pipe in an outer transaction group and checks that its identity and
duplicate-request provenance disappear after rollback. The test then reopens
the untouched copy, creates a pipe, saves a separate model and reopens it. It
checks the same pipe identity, type, system, level, diameter and endpoint
connectors, both expected to remain physically open, and verifies the original
RVT hash. Choose synthetic endpoints away from existing model connections.

The assembly compiled locally with zero warnings and errors. Running it
requires an installed and authorized Revit.TestRunner add-in and compatible
adapter assemblies. The fixture has not run inside Revit.
The fixture writes output paths, hashes and the reopened pipe UniqueId to
the console stream captured by the pinned TestRunner. Keep that output
with the NUnit XML and saved test artifacts when recording a native run.
The reopened model also gets a separate `reopened-inventory.json`. Use
the exact authored RVT and that inventory with `bsa revit-inventory-check`
to independently diagnose its saved geometry and connector evidence.

`CapturesConnectedElbowAfterSavedReopen` is a separate native inventory
control. It uses the same hash-bound synthetic request, with a horizontal
first leg and a pipe type whose routing preferences include a compatible
elbow. Choose endpoints in an empty part of the model with enough leg length
for the fitting. The test creates a perpendicular second leg and a native
elbow in a separate copy. It checks the two reciprocal physical connector
pairs, coincident origins and stable connector IDs before and after saving.
The test records the pre-save pairs and pipe-end coordinates in
`expected-connections.json`. Pass that
file as `--expected-connections` to `bsa revit-inventory-check` alongside the
authored RVT and reopened inventory to check the same pairs offline.
The test compiles against Revit 2027 and still requires authorized host execution.

The Automation build also contains the separate `AutomationCreatePipe` entry
point for a standalone, non-workshared test model. It uses `input.rvt` and
`pipe-request.json`, creates a single pipe using the existing transaction,
and saves to a fresh `authored.rvt` after the transaction commits. The
`creation.json` receipt records request, input, output and adapter hashes.
The inventory AppBundle still registers only the read-only entry point.
Select `--operation create-pipe` to stage its separate AppBundle and Activity.
With `--model` and `--pipe-request`, preparation checks the request's saved
RVT hash and copies the exact request bytes into the staging directory.
Preparation and stage verification also check the explicit identities, source,
finite endpoint coordinates and positive diameter before any host submission.
The write bundle was packaged locally from the compiled adapter. Work-item
execution and independent reopen remain pending.
[Autodesk Document.SaveAs](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/df74c7e1-a98a-7751-676a-e9b074566f62.htm)

For a separate reopen trial, stage the returned `authored.rvt` with the
read-only inventory Activity. Then reconcile both sets of local evidence:

```powershell
bsa revit-verify-automation-reopen --write-stage <stage-directory> --creation <creation.json> --authored <authored.rvt> --inventory <inventory.json> --reopen-preparation <preparation.json> --tolerance-m <metres>
```

MCP `bsa_verify_revit_automation_reopen` takes the corresponding
`write_stage`, `creation`, `authored`, `inventory`, `reopen_preparation`
and `tolerance_m` arguments. Use paths relative to the selected project root.
Both entry points only read saved evidence. Keep `inventory-request.json`
beside the reopen preparation receipt so its exact bytes can be matched to
the separate inventory capture and the authored model hash.

This checks the file hashes, compares the pipe identity and geometry with the
staged request, checks the creation readback's source, length and diameter,
and matches the two piping connector origins to separate curve
ends within the declared tolerance. It does not authenticate APS
execution, establish system connectivity or accept the design.

Current creation receipts include the native connector IDs and origins
captured after the creation transaction commits and before the enclosing group
assimilates. Reopen verification reports the creation and reopened
coordinates and their distance per ID in `creation_connector_readback`.
Earlier receipts without these coordinates leave `creation_connector_matches`
false. The current DLL passed local bundle verification with a Revit 2027
sample for inventory and a hash-bound synthetic fixture for pipe creation.
Both verifications were offline.

The integrated regression at `b73a9e5` passed all 42 Revit-selected tests
and 47 subtests. The matching Automation assembly also passed staging
and independent stage verification against the saved Revit 2027 sample,
with no upgrade required. The native host and saved reopening remain
unverified.

The Windows source candidate at `703bb72` was extracted and installed in
a fresh directory. Adding the optional `revit-metadata` extra there enabled
both installed interfaces. The CLI and MCP reports agreed on the saved
2024 release of the public Core Interior sample and its upgrade requirement
for a 2027 target.

Add `--model runs/<test-fixture>.rvt` to generate the hash-bound
`inventory-request.json` beside the AppBundle. The selected fixture stays
at its original path and outside the ZIP. Use those same RVT bytes as the
Activity's model input. The receipt records both the request and RVT hashes.
Run the same script with `--verify-stage <stage-directory> --model <original.rvt>`
to recheck the local files before a transfer. It checks file hashes and the
selected operation's XML entry point and Activity transfer names.
Add `--inspect-model` to check release compatibility and standalone model
requirements even when the staged receipt predates metadata collection.
To diagnose a returned Automation inventory, pass the original local RVT and
`--automation-receipt <preparation.json>` to `bsa revit-inventory-check`.
The corresponding MCP field is `automation_receipt`. The same field on a
`revit_inventory_check` workflow task takes a plan-relative path, whose
bytes are pinned for workflow integrity verification. The workflow verifier
also reconstructs saved diagnoses from the original inputs and checks the
recorded status. The diagnostic compares the
inventory's model, request and adapter hashes with the local preparation
record and permits the engine's separate `input.rvt` path. These checks
establish consistency with that record. Job execution and engineering
acceptance still require independent evidence.

Final observed build: zero warnings/errors. The initial build had desktop-reference conflicts; explicit WPF/WindowsForms framework references resolved them. The intermediate missing System.IO import was corrected. Evidence and source/binary hashes: ../../docs/evidence/moosas-review/revit-native-build.json.

`NativePipes.Create(UIApplication, PipeRequest)` must be called from a valid Revit API context on an explicitly selected test model. It checks active saved document identity, rejects existing edits/transactions, uses supplied type/system/level UniqueIds and metre-valued coordinates/diameter, creates a native Pipe and verifies dimensions/endpoints/two connectors. Any Revit failure message rolls back the transaction rather than being waived. No save/export or add-in registration is performed. The returned object explicitly leaves saved, system-connectivity and design acceptance false.

This is a compiled library, not an installed MCP/add-in or verified modeling workflow. Required next evidence: host invocation, positive and invalid-type/diameter controls, rollback/readback, source-bound saved reopening, actual joined pipes/fittings, sheets and visual review. The current method creates only one isolated pipe; it does not solve routing, select products, prove physical connections or establish Hong Kong compliance. Do not use it on the finished coursework or infer suitability from compilation.

`ElementProvenance` now attaches the serialized original `PipeRequest`, its SHA256 and the created element UniqueId through Revit Extensible Storage inside the pipe-creation transaction. It uses a versioned fixed schema GUID, rejects conflicting schema definitions and existing provenance, and reads back the payload before commit. Failure therefore rolls back the new pipe as well. Inventory exposes the stored request separately from current measured diameter/length; absent metadata is null, and copied metadata with a different element UniqueId is explicitly flagged. A request hash checks internal consistency only: it does not authenticate a source or establish that subsequently edited geometry still matches the request. Public schema access is intentional interoperability, not tamper protection. Source documents still require independent provenance binding.

This extension compiles against the installed API with zero warnings/errors; evidence is `../../docs/evidence/moosas-review/revit-provenance-build.json`. Native attach/read, failed-write rollback, save/reopen persistence, copy detection and later model-edit comparison remain unexecuted. Do not describe this as verified RVT persistence yet. API contracts were inspected in the installed `RevitAPI.xml` for SchemaBuilder.AddSimpleField, Schema.Lookup, Entity.Set/Get and Field.ValueType; no Autodesk binaries are redistributed.

## Explicit native creation entry point

Prepare a traceable request with `python -m bsa.revit_request --inventory <native-inventory.json> --model <saved.rvt> --basis <basis.json> --out <new-directory>`. The basis has exactly `source` and `pipe`: `source` declares a relative `path`, its `sha256`, and a nonempty `locator`; `pipe` supplies `PipeTypeUniqueId`, `SystemTypeUniqueId`, `LevelUniqueId`, `StartMetres`, `EndMetres`, and `DiameterMetres`. These are declared design inputs, not automatically extracted measurements. The selected identities must exist in the supplied inventory, whose model path/hash must match the saved RVT. Source bytes and all input hashes are retained. Output `pipe-request.json` embeds source path/hash/locator and basis hash in `Source`; `preparation.json` records the input and request hashes. The tool does not infer hydraulic internal diameter, check product suitability, validate the semantic meaning of a source locator, or invoke Revit. Native short-curve/type acceptance remains a host check.

Twenty Revit logic/workflow/request tests pass, including source/model changes, invented selection IDs, nonfinite coordinates, Boolean diameter, zero-length segments and refusal to overwrite outputs. Request-binding tests explicitly use non-RVT fixture bytes to test hashing and routing only; they do not establish real inventory provenance or native model execution.

`CreatePipeCommand` is an original `IExternalCommand` with manual transaction mode. It opens a JSON request picker, accepts the `PipeRequest` fields documented in `NativePipes.cs`, requires the request and named RVT under this repository, checks request bytes before execution, and delegates active-document/transaction guards to `NativePipes.Create`. The preparation CLI embeds `SavedRvtSha256`. Before starting a transaction, the native adapter hashes the matching active document's saved RVT and rejects missing or stale hashes. Regenerate older executable requests from a matching inventory. Historical provenance remains readable and duplicate prevention excludes the revision hash. Success reports the returned element identity and explicitly says the model is not saved. The command opens no model, saves no RVT and supplies no default geometry or type identifiers.

The revision guard compiled in an isolated artifacts directory against the
installed Revit 2027 API using the pinned .NET SDK 10.0.403, with zero warnings
or errors. Python tests checked that the producer carries the correct RVT
hash. Native transaction and save/reopen behavior remain unexecuted.

`scripts/prepare_revit_addin.ps1 -Model <repo-local.rvt> -Out <new-directory> -IncludeCreationCommand` additionally writes `Bsa.CreatePipe.addin`. Default preparation remains read-only inventory only. Actual preparation at `runs/revit-command-entry-v1` generated both manifests, and XML readback confirms the creation class and assembly. Compilation passes with zero warnings/errors after qualifying Revit's TaskDialog against the Windows Forms type. Inventory and creation entry points accept UTF-8 BOM-prefixed requests from Windows PowerShell. This does not register or load either command, and the named test RVT is not yet created. Native invocation, cancellation, rollback and saved persistence remain pending. The command is not idempotent across a later saved session: after uncertain execution, inspect the model/provenance before any retry.

## Inventory execution

An alternative manual host path now captures the compiled adapter in a Dynamo graph:

```powershell
.venv/Scripts/python scripts/prepare_revit_inventory_graph.py --model runs/revit-sample-inventory-v1/plumbing-test.rvt --adapter adapters/revit/bin/Release/net10.0-windows/Bsa.Revit.dll --out runs/new-revit-dynamo
```

The `--adapter` mode copies the current BSA DLL into the new run folder, pins DLL/request hashes in the embedded PythonNet3 code and calls the C# `InventoryCommand.Run` through `DocumentManager.Instance.CurrentUIApplication`. It verifies the returned assembly location to reject reuse of a different loaded assembly. It opens no model and performs no add-in registration. Without `--adapter`, the previous Python implementation remains available but lacks the current C# inventory fields. Preparation at `runs/revit-sample-dynamo-v1` succeeded, including embedded Python syntax compilation; Dynamo graph loading, PythonNet3 interoperability and native invocation remain unverified. If loading fails, retain that failure rather than changing host security policy or restarting the user's application automatically.

Creation now searches existing BSA Extensible Storage records before starting a write transaction. An identical deserialized/reserialized `PipeRequest` is rejected with the existing element UniqueId, including copied elements carrying that request. The caller must inspect current geometry; the guard does not return success merely because history exists. Malformed stored payloads remain errors. This is exact-request duplicate prevention, not general geometric deduplication or a distributed idempotency protocol: changed source/path text, deleted provenance or altered request fields may not match. The new guard compiles with zero warnings/errors but its live repeat-after-save, copied-element and changed-geometry controls remain unexecuted. The earlier instruction to inspect state after an uncertain write still applies.

Saved inventory diagnosis is available as `python -m bsa.revit_connectivity --inventory <inventory.json> --model <source.rvt> --tolerance-m <explicit-metres> --out <new-report.json>`. Paths must remain inside this repository; the saved RVT path/hash must match the inventory and both inputs must remain unchanged. The tolerance is an explicit diagnostic choice, not a regulatory or installation allowance.

The workflow adapter `revit_inventory_check` accepts `inventory`, `model` and positive finite `tolerance_m`, plus ordinary `id`, `requires_pass` and optional `description`. Paths resolve against the source plan. It emits `diagnosis.json` with source hashes and preserves diagnostic `fail` or `pending`; it never promotes internally consistent data to a passing native-system gate. Put its task ID in downstream `requires_pass` to block dependent drawing/delivery work. Existing workflow source/artifact hashes detect later changes. Three workflow tests execute the adapter and dependency diagnosis using explicitly labelled non-RVT fixture bytes; they verify stale-hash rejection, failure propagation and pending-delivery gating, not native model validity. All sixteen Revit logic/workflow tests pass. Actual Revit inventory production remains the prerequisite for a real project run.

The current native inventory includes both measured curve endpoints, curve kind, native pipe/system-type UniqueIds and reference-level UniqueId. `bsa.revit_revision.audit_pipe` compares these observations plus diameter/length with stored creation intent and is invoked by the inventory diagnostic. A translated segment is detected even when length and diameter are unchanged; endpoint reversal alone is tolerated. Type/system/level changes, copied provenance and non-straight curves are flagged. Missing creation records stay pending. An intentional revision requires separately approved updated design evidence; this tool neither rewrites history nor assumes every difference is an engineering defect. Source declarations remain unverified. Thirteen synthetic connectivity/revision tests pass; the native collector compiles without warnings/errors. Actual Revit capture and saved-reopen comparison remain pending.

The diagnostic compares reciprocal references against the opposite connector record (not just its claimed Boolean), physical flags, API relations, domains, target coordinates and independently recomputed separation. Missing equipment/accessory targets stay pending; open connectors are listed without inventing terminals or treating all openings as defects. Even internally consistent evidence remains pending with exit code 2 and `connected_system_verified=false`. It does not infer hydraulic continuity through a fitting from its family identity. Eight synthetic fault-injection tests pass, including stale positions, one-sided references, logical references, omitted equipment, open ports and malformed evidence. No real RVT inventory has yet been produced or diagnosed; these controls verify diagnostic logic only.

The current C# inventory also collects native pipe-fitting family instances and reports missing connector managers explicitly. Each connector retains its domain/type, physical `IsConnected` flag (null for logical connectors), external references, reciprocal-reference evidence and endpoint separation in metres. `IsConnectedTo` is recorded as an API relation rather than promoted to physical-system acceptance. Logical connector origins and distances remain null instead of making unsupported physical queries. This follows the installed Revit 2027 `RevitAPI.xml` contracts for `Connector.IsConnected` and `Connector.IsConnectedTo`.

The extended source compiles with zero warnings/errors (`../../docs/evidence/moosas-review/revit-connectivity-build.json`). No host execution has occurred: runtime handling of connector varieties, joined/unjoined controls, fitting coverage, saved reopening and full system traversal remain pending. The report explicitly retains `connected_system_verified = false`. Accessories, equipment, flexible pipes and linked models are not included; a missing item must not be interpreted as an open network endpoint. The separate Python inventory has not yet acquired these additional fields.

`InventoryCommand` implements IExternalCommand with TransactionMode.ReadOnly. Its Execute entry opens a request-file picker; `Run(UIApplication, requestPath)` is also callable from a valid API context. The request contains absolute `DocumentPath` and `ReportPath`; the JSON and both paths must reside under this repository. It rejects family/unsaved/mismatched documents, checks model and request bytes before/after collection, and creates a new JSON report with model/request/assembly hashes. It reads native pipe/type/system/level identities and connector references. Logical references, linked models and physical connectivity remain outside acceptance. It opens no other documents or transactions.

From the repository root, prepare a local manifest and request:

```powershell
./scripts/prepare_revit_addin.ps1 -Model runs/revit-native-v1/test.rvt -Out runs/revit-addin-v1
```

This command only prepares files; it does not register the add-in, restart Revit, or claim that the RVT exists. `InventoryCommand` compiled with zero warnings/errors against the local API. Its current build evidence is ../../docs/evidence/moosas-review/revit-inventory-build.json; the earlier native-pipe evidence identifies an older assembly. Manifest XML was generated and read back. Actual registration, loading, invocation and readback are still pending desktop availability. Generated manifests reference the current build output, so regenerate/review hashes after rebuilding. The Python/Dynamo route remains an alternative pending path, not another verified implementation.

Host integration follows Autodesk's [IExternalCommand reference](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/ad99887e-db50-bf8f-e4e6-2fb86082b5fb.htm) and [transaction-mode contract](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-API-MainReference/files/html/84254a1f-7bba-885a-ce65-e68fc238fddb.htm).

## Local deployment review bundle

Run `python scripts/prepare_revit_handoff.py --out runs/<new-review>` from the
repository root after a reviewed build. The allowlisted ZIP contains only
Bsa.Revit.dll, Bsa.Revit.deps.json and a review manifest. It excludes Autodesk
references, PDBs and models, verifies archived bytes against the input files, records
current C# source/project/SDK hashes and rejects existing or outside-runs output.
It does not compile, sign, register, upload or invoke the adapter; source hashes
alone do not prove that an arbitrary existing DLL was built from those sources.

On 2026-11-10 a fresh Release build completed with zero warnings/errors, followed by
actual bundle preparation and archive readback. Authenticode still reports NotSigned.
Existing-output and outside-runs controls reject. The bundle is retained locally
under ignored runs, not published as a release. Owner license selection, an approved
trust/deployment basis and the full native validation sequence remain pending.
