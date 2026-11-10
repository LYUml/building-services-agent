# Revit signing deployment investigation

Checked 2026-11-09. This is a deployment investigation, not a signed release or native execution pass. The actual local command invocation was blocked by Code Integrity events 3077/3033; see [captured evidence](evidence/moosas-review/revit-native-policy-block.json). The current user's certificate store had zero code-signing certificates on inspection. No trust store or security policy was changed.

## Candidate services

[SignPath Foundation's conditions](https://signpath.org/terms) offer free code signing to qualifying open-source projects. They require an OSI-approved license, an existing release, verifiable source builds, project roles and manual signing approval, and signing-policy/privacy disclosures. Acceptance is discretionary. This repository currently has no root LICENSE file and no verified signing service configuration. Public GitHub visibility is not an open-source license. Do not claim SignPath sponsorship or add its sponsorship wording as a current fact before acceptance.

The Foundation distinguishes project-owned binaries from upstream binaries: its project certificate cannot simply be used to sign arbitrary upstream engines. Therefore this candidate would not by itself resolve the local Radiance, SWMM, EnergyPlus, FreeCAD or MOOSAS native blocks. The original Revit adapter depends on proprietary Autodesk API references supplied by the user's installation; whether that external dependency fits the service's eligibility rules remains unconfirmed. Do not redistribute Autodesk DLLs to construct a signing package.

[Microsoft Artifact Signing setup](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart) currently limits individual public-trust identity validation to US/Canada. Hong Kong workspace location does not establish the owner's legal identity or eligibility; do not assume this is an available personal service. Identity verification, account creation, payments and acceptance of provider terms are not completed by this investigation.

## Preparation and remaining acceptance

The original adapter now declares Product `Building Services Agent`, Title `Building Services Agent Revit Adapter`, Version `0.1.0` and deterministic compilation. These attributes support identifying a future signing artifact; they do not create a signature or prove reproducibility across machines. Existing manifests point to mutable build output: rebuilding changes the binary identity, so historical hashes in preparation/load evidence must remain historical.

Before a signing integration is selected, the repository owner must choose a distribution license and establish eligibility with a provider, or supply an already approved signing identity/deployment environment. Prepare the exact candidate package and verify proprietary references are excluded; pin any signing action/tool before adoption. No signing action or service has been installed in this milestone.

After supported signing, verify Authenticode and certificate chain on the exact DLL, record the signed hash, regenerate preparation evidence, and invoke the command on the saved test copy. A valid signature alone does not prove acceptance by the machine's recorded policy. Native inventory, creation/rollback, connectivity, save/reopen, schedules, drawings and full engineering acceptance still require actual host evidence. Do not change loaders or disable application control to clear this gate.

A local review-bundle preparer is now available at scripts/prepare_revit_handoff.py.
Actual 2026-11-10 build and byte-checked ZIP preparation include only the original
adapter DLL, dependency manifest and review metadata; no Autodesk binaries or models
are included. This is preparation for an authorized deployment decision, not a
signature, provider approval or remedy for the recorded host policy block.
