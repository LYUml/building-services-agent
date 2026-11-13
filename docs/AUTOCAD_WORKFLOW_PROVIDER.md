# Upstream AutoCAD writer in the existing task chain

A `duct_sheet` task may now select `"writer": "uc4n"`. Omitted writer or `builtin`
preserves the existing route; other names reject. The pinned MIT upstream and
exact dependencies remain documented in AUTOCAD_SCHEDULE_PROVIDER.md. This is
thin orchestration glue, without a new drawing engine or dependency.

```json
{"id":"sheet","kind":"duct_sheet","depends_on":"duct","drawing":"source.dxf","binding":"binding.json","writer":"uc4n"}
```

The parent must remain the original duct_schedule task. Its optional allocation
parent is inherited from that same plan, with no task-specific replacement inputs
or document-selected runtime. Source binding must already be reviewed. The bridge
checks the actual producer hash, reruns the source-backed writer calculation,
requires equality with the inherited schedule, then independently verifies source
and drawing evidence. It retains every original requirement and ordinary gap.
Numerical replay is deliberate comparison overhead; no speed benefit is claimed.

The downstream existing duct_sheet_native task consumes the verified output with
its producer hash. Missing/failed allocation or schedule blocks writing and native
consumers. Changed producer or unknown writer fails. Workflow verification also
runs the upstream writer verifier and checks exact source/producer correspondence;
rehashing a forged receipt cannot replace replay. Full acceptance remains pending.

## Real complete-plan replay

Only writer selection changed in a new sibling of the original BSE3227 plan;
the original was preserved. All 16 tasks and 33 requirements remain. Five scoped
executable stages pass: air allocation, terminal lookup, duct schedule, writer,
and actual native DWG save/reopen/plot. Eleven regulatory/manual tasks stay pending,
including the original soft-duct applicability check and six unresolved inputs.
The command returns 2 for that incomplete whole-plan result, as intended.

The writer covers 47 sections, 235 bound cells and 47 arrows. Native geometry
reconciles across nine layers. Final A1, enlarged schedule and notes were actually
inspected; all rows readable, no observed table overlap/clipping. The PDF page
content matches current public delivery, so existing binaries remain unchanged.
This is a repeat of the interpreted task graph, not autonomous interpretation,
complete professional design or full Hong Kong compliance. See the aggregate
in evidence/autocad-workflow-provider.json; raw coursework/runtime remains private.
