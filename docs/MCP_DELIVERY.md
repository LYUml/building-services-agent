# MCP source-bound delivery review

After bsa_artifact_index, inspect its original requirements, source locators,
acceptance targets and recorded evidence paths. Read actual artifacts with
bsa_read_artifact. Use bsa_delivery_template(plan,out,review) to save a fresh
separate JSON review and obtain its contents. Every requirement starts pending.
The review must be outside the immutable workflow directory; existing files
cannot be overwritten. All caller paths are confined to the host project root.

After actual inspection, prepare a fresh complete review with bsa_save_json and
assess it using bsa_assess_delivery(plan,out,review). Exact fields and supported
Boolean fact checks are documented in DELIVERY_REVIEW.md. Preserve every
requirement and source/report fingerprint. Cite actual recorded artifacts and
hashes; reviewer names and timestamps are assertions, not authentication.
Do not record a whole requirement as pass based on one adapter Boolean flag.
Keep unexamined obligations pending and describe the limited observation.

The result retains original quotes, locators, execution/recorded/effective review
statuses, blockers, evidence and engineering requests. Invalid or stale records
return failed audit results; they do not rewrite execution. A pending automated
task or blocked manual task cannot be cleared by typing pass. Overall
review_checks_pass concerns the defined evidence records only; design_accepted
remains false and engineering_acceptance remains not_established.

These two tools reuse bsa.delivery.template/assess through the fixed isolated
worker. No reviewer generator, new approval engine or dependency is added.
Native CAD/BIM, visual and full regulatory acceptance remain separate checks.

Validation: actual eighteen-tool stdio client retrieves all five requirement
rows, creates an all-pending record and obtains needs_review with design_accepted
false. Unsupported pass without cited artifacts fails; template overwrite
rejects. Existing JSON/IFC reads, tamper controls and pump recovery still execute.
Fifteen MCP/delivery tests pass, zero skips, 64.257 seconds. This verifies
protocol and review semantics, not completed engineering review.
