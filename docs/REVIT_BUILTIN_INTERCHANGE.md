# Actual Revit test-model opening

Revit2027.3 was started with no previously running Revit process or open model.
A new repository test copy of the historical plumbing sample was opened through
the normal file dialog. The original and copy retain identical SHA256 bytes
before and after the UI trial. Neither was saved by the agent. The application
and test model remain open; no unsaved document was closed or application restarted.

The actual model load reported zero errors and39warnings, including an unenclosed
space. A second dialog identified four unresolved architectural, electrical, HVAC
and structural links. These were retained for this scoped main-model inspection;
they are not repaired or accepted. The plumbing cover sheet and model browser
were visible after opening. This establishes opening one existing RVT, not native
MEP inventory, connector measurements, creation, physical connections or persistence
of an authored change.

The next attempted step was built-in export navigation, using the existing Revit
installation rather than loading the blocked original adapter. Native application
accessibility was readable in the normal model view, but became unavailable with
the File menu expanded. Fresh screenshot/coordinate attempts dismissed the menu
instead of reaching an export dialog. Both available computer-use interfaces
exposed this limitation. No IFC file was produced. Availability or successful
execution of the IFC export command is therefore not verified by this trial.

No add-in was registered or invoked, and no security/trust setting was changed.
The historical Code Integrity block remains a separate deployment issue, not the
observed cause of this menu-navigation failure. Do not call this trial a remedy
for that block or retry the blocked DLL through another loader.

Next acceptance evidence still needs a working built-in UI invocation or an
approved native deployment, exact active-document identity before every write,
explicit output/configuration, actual saved IFC inspection if exported, and a
source-bound account of omitted links and warnings. An IFC export would only
establish that scoped interchange path. Native Pipe/connector creation, failed
transaction rollback, saved reopening, schedules, drawings and engineering
acceptance require their own actual evidence. See REVIT_SIGNING.md and
adapters/revit/README.md.

The aggregate record is evidence/revit-built-in-open-check.json. Test RVTs and
private runtime observations stay under ignored repository runs; no Autodesk
sample model or proprietary binaries are redistributed. No engineering unit test
is claimed for this manual host-application observation.
