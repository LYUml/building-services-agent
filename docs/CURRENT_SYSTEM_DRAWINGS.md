# Current source system drawings

Three actual A1 system sheets now complement the current open-plenum coordination plan: one main sheet and two terminal sheets covering 20 VAV groups. All use unchanged IFC a26626e4359ca82ca90de33423d46819b66bd78e54f22a0f52e221ff18ce2937. The 598-row component index maps visible aliases to native source GUIDs.

AutoCAD saved and reopened all three DWGs; native editable correspondence passes (3228/3650/3650 entities). Independent reopened DXF reads verify all 598 visible component labels and all 80 terminal maximum/minimum flow strings against current prescribed-demand cases. Actual final PDF pages and representative terminal crops were visually inspected. See [receipt](evidence/current-system-drawings.json).

Reused existing IFC directed-port extraction, Graphviz 13.1.2 (EPL-2.0), rectpack 0.2.2 (Apache-2.0), ezdxf and shared drawing/native AutoCAD adapters. No new engine or dependency. Port-constrained routing experiments were rejected and restored before publication; larger orthogonal spacing and two terminal sheets use the existing verified path.

Course outputs: 03_Design_Drawings/Connection_Layout/Current Open Plenum Study/System Diagrams. These are a separate study and do not replace the course report or adopted baseline. SD labels denote connection planes. Schematic lengths are not installed lengths; pressure, VAV control losses, physical installation and ADPI applicability remain unaccepted.
