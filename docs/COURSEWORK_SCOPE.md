# Reviewing coursework scope and design assumptions

## Executed current-agent replay

A fresh private-project refresh and full HVAC execution retained all 33 source
requirements and six unresolved inputs. Six postprocessing/report stages completed
without execution errors. The source-bound package inspection passes; native DWG
was freshly saved/reopened and its plotted reference passes. Both the one-page
drawing and all 24 report pages were rendered; overview inspection found no
clipping or overlap. Report and drawing page content streams and extracted text
match the previous outputs; this comparison does not independently prove building
scale, engineering applicability or installed geometry.

The host AI separately recomputed rule-of-thumb total/sensible thermal power and
air balance using Decimal arithmetic, preserving given and assumed inputs. All
80 source terminal IDs and each 40-percent minimum flow reconcile, with maximum
and minimum flow conservation. Four explicitly scoped load/turndown requirements
now have evidence-backed effective review passes; the other 29 remain pending.
The separate audit has no consistency issues and remains needs_review, with
design_accepted=false. Original execution statuses and source quotes are unchanged;
the review is a host AI assertion, not authenticated professional signoff.
See evidence/current-hvac-scoped-replay.json. Private sources, runs and detailed
review records remain in the selected coursework workspace.

The official [Krueger engineering guide](https://www.krueger-hvac.com/file/9261/GRD_Engineering.pdf),
printed page a1-11 (PDF page 11), explicitly associates Model 1400 with Type 3
circular ceiling airflow. This differs from merely classifying the product by its
square face or louvered family. Its cooling-load graphs do not authorize replacing
a classroom table, inventing interpolated graph values or clearing unknown load,
characteristic length or installation facts. Keep each category assertion bound
to its selected source/edition. The existing course-specific mapping remains
limited to that classroom method; this replay does not change the ADPI criterion.

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

## Conditional turndown arithmetic

When the brief explicitly supplies a minimum-flow factor,independently check every current terminal ID and multiply its retained maximum flow by that factor. A scoped arithmetic review can depend on the passing allocation rather than physical-layout acceptance,provided the result is explicitly conditional on that maximum-flow allocation. Preserve the original issue and dependency change in a planning record,new plan and fresh run;keep all original requirement IDs/quotes and unrelated blockers. Product throw,ratios,ADPI,actual room loads and installation remain separate requirements,even when the same source paragraph contains all of them. The actual coursework trial checked80terminals at0.4,retained33requirements,resolved only the arithmetic issue,and recorded2scoped manual passes with31review rows still pending. Coursework evidence stays in its project workspace.
