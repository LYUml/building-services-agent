# Linked annotation visibility controls

Source: ../saved-route-audit/native-export.dxf and source-layout.json; IFC and source rows remain in ../elbow-riser/workflow.zip. Existing evidence was not rewritten.

before.json records four deliberate mutations incorrectly accepted before this patch. controls.zip retains those files plus an actual raw group-67 mutation. after.json records all five rejections and their hashes. actual-native-audit.json records the unchanged native export passing the new checks.

The initial 20-case regression failed two paper-space controls because ezdxf repaired the mutation when saving. The corrected tests inject serialized tags and assert their presence. The corrected saved-audit run passed 13 cases, including fresh IFC extraction, unrelated paper-space legends and binary DXF; the native route regression passed eight cases with BSA_TEST_AUTOCAD=1, no skips. This is 21 scoped tests, not a full-suite result. Native logs retain PDF duplicate-PageMode and IFC destructor diagnostics; unittest exited successfully. No new visual acceptance is claimed.

Only raw/loaded paper-space markers, entity invisibility and layer off/frozen/plot flags are checked. Locked layers are valid. Transparency, colour, plot styles, viewport clipping, glyphs and complete engineering acceptance remain outside this check.
