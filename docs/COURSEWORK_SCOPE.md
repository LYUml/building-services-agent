# Reviewing coursework scope and design assumptions

Read the original brief and its referenced material before using a pending-input
register as a work list. Preserve every actual deliverable and engineering
obligation. A deliberately preliminary calculation can use declared design
assumptions when that matches the requested task. Its source provenance and
limited purpose must remain visible.

For a brief that explicitly requests rule-of-thumb cooling and total supply
airflow,review the given load area,the course allowance and approximate sensible
fraction. Distinguish adopted density/heat capacity and room/supply temperatures
from supplied or measured conditions. Independently check the thermal balance:

```
total cooling W = load area m2 * allowance W/m2
approximate sensible W = total cooling W * prescribed approximate sensible fraction
volume flow m3/s = approximate sensible W / (density kg/m3 * heat capacity J/(kg K) * temperature difference K)
```

Keep thermal cooling/sensible power distinct from electrical input or kVA.
Document the uncertainty introduced by approximate sensible fraction and the
selected temperature difference. An unverified detailed room sensible load does
not alone prevent the explicitly requested preliminary calculation. It remains
unverified for ADPI applicability or another method that needs it.

The same source passage can contain load,layout,product,throw and ADPI obligations.
Retain their separate requirement IDs and exact original source quotes. A scoped
load review cannot accept the other obligations merely because their quote is
identical. A single-line drawing request also retains its own actual geometry,
connection,length,scale and visual checks. Broader BIM,physical fittings,complete
network pressure,installation and jurisdiction capabilities stay in the agent's
development scope and must be verified before claiming them.

## Evidence-backed resolution with existing tools

1. Preserve the original plan,run and unresolved-input record.
2. Pin actual brief/reference bytes and rendered-page observations. Record why a
   missing item can be a declared assumption for this exact preliminary task,
   and which other tasks still need it as a verified fact.
3. Derive a new plan with unchanged requirement texts,IDs and deliverables. Store
   the resolution and original issue in a source-linked `planning_records` file.
   Remove only the specifically resolved blocker. Retain all unrelated gaps and
   declare the actual numerical producer as a `requires_pass` prerequisite.
4. Validate and execute the new plan into a new directory. Recompute the result
   independently and inspect source/classification/units. Do not edit old statuses.
5. Use the separate delivery template/audit in DELIVERY_REVIEW.md. Record only
   the examined subrequirements with source-bound artifact hashes and substantive
   observations. Preserve every other requirement as pending or failed according
   to its evidence.

This uses existing plan validation,input discovery,workflow execution and delivery
review. No new requirements parser or engineering solver is introduced. A written
resolution remains a reviewer assertion;neither `planning_records` nor hash
consistency independently proves its engineering interpretation.

## Executed scope

An actual private brief explicitly requested the preliminary calculation. Its
original pages and course reference were inspected;declared assumptions and
given area were kept separate from unresolved geometric area/scale and detailed
room load. Independent decimal arithmetic reconciled the newly executed result.
All34 original requirement records were preserved. Two scoped manual review rows
pass;32 remain pending,with full design acceptance false. The original manual
execution state remains pending,as required by the delivery protocol.

The actual new package executed seven stages without stage errors,including
native drawing reopening/plotting. Fourteen delivery/input-issue tests
pass,covering blocked manual reviews,failed/missing engine tasks,changed source
registers,artifact mutations and preserved pending acceptance. These controls
check review consistency,not an automatic interpretation of arbitrary briefs.
See evidence/coursework-preliminary-review.json. Private course documents,
requirement quotes,calculations and review records remain local.
