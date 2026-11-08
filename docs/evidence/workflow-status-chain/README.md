# Multi-level dependency diagnosis

Executed the existing water-riser/coupled-plan.json with only network_model_design.run fault-injected to raise a controlled error. Electrical calculation and artifact generation, plan validation, dependency dispatch and diagnostic integrity verification actually ran. The water failure blocks pump, the two-input pump/electrical coupling, and its downstream drawing/QA. Both blocked coupling parents trace to one deduplicated water action task. Independent electrical execution passes and retains artifact evidence.

This proves declared dependency tracing, not a real hydraulic failure diagnosis or water-engine execution. Twelve workflow/status tests passed; the updated building-services-design skill passed its structural validator. No claim of complete design acceptance is made.
