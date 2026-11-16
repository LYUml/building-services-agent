# Native K-Select ADPI feature check

Authorized temporary computer use now actually opens the installed GRD10.0.2
ADPI Calculator for1400/24x24/8inch. It identifies Type3 Circular Ceiling Pattern,
with CFM, ft, degF and sf inputs. Area is described as single-diffuser coverage;
L as device-to-wall or device-to-neighbour-midplane distance. This does not itself
resolve every manufacturer installation condition or establish actual room loads.
The independent MCP project remains unchanged; its advertised API still has no
ADPI operation.

The observed input path dropped the decimal point in L; precise original inputs
remain unresolved. No integer-input limitation is inferred for all native controls.
A clearly rounded393CFM/6ft/22F/170sf diagnostic displays sensible load55BTUh/sf
and is rejected by ADPI Range Check: reported throw16ft lies outside the stated
0.1-1.9ratio calculation range. No valid ADPI results; stale0 is not physical ADPI.

A separate hypothetical16ft-L diagnostic, with the other inputs unchanged,
actually displays ADPI82.9, Max84.3/Min70 at the same displayed load55BTUh/sf.
It proves the native prediction feature can operate at that load, not that the
course layout passes. The16ft length is not in the submitted layout. Exact32case
critical verification and native PDF export have not occurred. The screenshot and
range message remain private; only their hashes and scoped observations are public.

Performance values are restored at393CFM with no dialogs; the native program
retains an ADPI row label/info after switching modes, so no fully unchanged UI
claim is made. No project schedule/report/drawing was saved or modified.
Course acceptance remains deferred. See [executed receipt](evidence/native-adpi-ui-check.json).
