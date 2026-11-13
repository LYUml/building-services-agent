# Real AutoCAD source intake through a reused upstream backend

The current thin adapter combines existing trusted AutoCAD Core Console DWG export
with U-C4N/Autocad-MCP's independent EzdxfBackend at commit
6f6a538255ca9f885232e845ac32f10b4433fe3e (MIT). It imports the backend in a fresh
worker with CAD_LAUNCH=never, without installing its complete FastMCP3 server,
instantiating live COM, or altering host application policy. Existing ezdxf 1.4.5,
pydantic 2.14.3 and numpy 2.5.4 are pinned; upstream source must be clean/exact.
No drawing engine or numerical solver is reimplemented. The original MIT notice
is retained under third_party/licenses/uc4n-autocad-mcp-6f6a5382.txt.

## Host usage

From this editable tool checkout, obtain the upstream source under
tools/autocad-uc4n-review and checkout the exact commit above. Install the optional
`autocad-source` extra; ezdxf is already a base dependency. Real coursework paths
are selected only by explicit host BSA_PROJECT_ROOT, never by document content.

```powershell
$env:BSA_PROJECT_ROOT='C:/ABSOLUTE/COURSEWORK'
python -m bsa.autocad_source run C:/ABSOLUTE/COURSEWORK/source.dwg --out C:/ABSOLUTE/COURSEWORK/fresh-inspection --autocad "C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe"
python -m bsa.autocad_source verify C:/ABSOLUTE/COURSEWORK/fresh-inspection
```

The source is copied before native export and the isolated active-document path
is checked before DXFOUT. The DXF backend receives a separate exported copy.
Source, engine and method hashes, native intake, worker output, raw inspection
and artifact hashes remain in the selected project. The verifier independently
re-reads exported handles/types/layers and layout names and checks current
provider/dependency identity. Failed worker/native evidence remains failed.
This is a host CLI/library path; no new client MCP tool or desktop setup is claimed.

## Actual same-source result

On the BSE3227 original source DWG, the adapter preserves original bytes and
matches 3,894 model-space entity handles/types/layer assignments, 16 layers and
three layouts. Header INSUNITS=4 reports millimetres; it does not independently
prove actual building dimensions or physical scale. Blocks/attributes, layout
and other raw metadata are available for interpretation; nested block/proxy/
xref geometry and paper-space contents/plot scale are not fully accepted.
Four actual upstream-backed tests exercise the same library on a public DXF,
block/layout coverage, source/result tampering and project confinement.

## Other candidate's actual failure

The pinned dcc-mcp-autocad 0.1.3 trial used commit
d2acd4859b5a724b6032bd3044684291972a26e2, dcc-mcp-core 0.20.36 and
dcc-mcp-server 0.20.53 in an isolated ignored environment. Import of its framework
_core failed under host Application Control, before any native AutoCAD call.
The source remained unchanged. No policy override, DLL renaming, security-setting
change or success claim was used. This result does not mean AutoCAD itself failed;
the existing native exporter completed on the same source. That framework path
is not selected for this host at present.

This milestone establishes source intake only. Actual engineering changes,
editable DWG write/reopen and every required scale/visual plot remain the next
real-task gate. All original ordinary gaps and complete Hong Kong/engineering
acceptance remain pending. Public evidence is aggregate only; private source,
raw inventory and runtime records remain ignored in the project.
See evidence/autocad-source-provider.json and AUTOCAD_PRIORITY.md.
