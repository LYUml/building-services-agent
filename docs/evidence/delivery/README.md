# Source-bound review execution evidence

Actual execution of `examples/delivery-plan.json` in `runs/delivery-release`, followed by a separately authored review and `runs/delivery-audit-final`. Source/task-artifact byte integrity remained valid. The workflow's original report/statuses were not rewritten. Completed coursework is not used or modified.

`workflow.json` records successful conditional electrical generation and two pending manual tasks. `review.json` pins the exact plan/run and every requirement, with cited artifact hashes, actual observations and Boolean fact checks. `audit.json` and `report.html` retain effective results: R1 numerical evidence pass, R2 scoped SVG review pass, R3 fault/protection pending. Overall status is **needs_review**, with review_checks_pass and design_accepted both false.

`calculations.json` supports the source-based numerical review: 0.12 kW connected input, 133.333 VA, 0.579710 A, corrected ampacity 14.4 A and 0.146188 percent voltage drop. The source DXF was independently reopened and its three device circles counted. These values use the explicit synthetic input assumptions and do not validate fault protection or regulation compliance.

`preview.svg` is the original generated artifact. `preview-render.png` is an actual isolated headless Edge rendering inspected for three distinct symbols, readable L1/L2/L3 and LGT-1 labels, and clear margins without visible overlaps/clipping. The review binds the rendered image to the exact source SVG hash. It is schematic SVG evidence, not native DWG, PDF scale, printed quality or full drawing acceptance.

`false-fact-review.json` records a deliberately contradictory assertion that design_accepted should be true. `false-fact-audit.json` shows the actual false adapter flag overrides that recorded pass and fails the audit. Tests also exercise omitted/duplicate requirements, changed source acceptance/locators, stale matrices, altered artifacts/attachments, invalid evidence paths, failed tasks and pending engines.

`regression.log` retains full local tests with optional engines enabled. Paths/hashes reference original ignored run directories; this selected archive is not a complete portable run bundle. Reviewer metadata is not authenticated; audit consistency does not prove semantic completeness or professional certification. The missing fault/protection evidence remains unresolved.
