# Gazal performance policy v1.0 — pilot

The score summarizes documented work. It does not measure employee worth and is not an AI prediction. Use it for feedback and workload support. Performance results and policy are visible only to account administrators and the super administrator. Employees may request correction of task records through their manager; automated appeal tracking is not yet implemented. Never automatically determine salary, discipline or termination from this score.

## Formula
Score = 0.40 × quality + 0.35 × punctuality + 0.25 × completion.
All components range from 0–100 and task complexity (1–5, set before assignment) is the weight. The rolling window includes tasks with an effective deadline in the last 90 calendar days, including today. Deadline comparisons use Africa/Lagos date boundaries. Compare within similar roles and task types, not a universal employee ranking.

- Quality: weighted mean of approved-task quality reviews. Review rubric: correctness 40 points, acceptance criteria 30, reliability/testing 20, documentation/handoff 10. Managers enter the combined 0–100 rating; separate rubric fields are not yet collected. Review against written acceptance criteria, not subjective popularity.
- Punctuality: weighted percentage of approved tasks whose final submission was by the effective deadline. Approval delay is excluded. A revision resubmission updates the submission date; external rework requires an approved deadline exception.
- Completion: weighted approved work divided by all eligible due work. Submitted but unapproved work remains pending; managers should review promptly and approve exceptions when delays are outside employee control.
- Exclusions: cancelled tasks, tasks currently on hold, and explicitly excluded tasks. Manager-approved deadline adjustments and exclusions require at least a ten-character reason, with actor and timestamp retained in an append-only audit history.
- Evidence gate: at least five eligible due tasks, five approved tasks, and quality and submission timestamps for every approved task. Missing evidence produces no score. Display sample sizes alongside the score. These thresholds are pilot choices, not scientifically validated reliability thresholds.

Publish this policy to employees before use. Review complexity assignments, manager-rating consistency, exception frequency and missing evidence monthly. A policy change should create a new version and never silently rewrite previously published scores. Current scores are recalculated and historical snapshots are not yet implemented. This pilot has one application-wide policy; per-account customization is a future milestone.

## Predictive AI development policy
Keep individual performance scoring separate from project traction. Revenue/user growth is context, not an employee score or proof of individual causality.

First forecasting target: risk that a task misses its adjusted deadline. Labels must distinguish late submission from late manager approval. Features must come only from information available at the forecast time: remaining time, complexity, prior completed work, dependency/blocker state, documented capacity, and role/task type. Do not use protected traits, inferred health, personal communications, biometrics or monitoring outside assigned work. Blockers and capacity need structured fields before training.

Store immutable weekly score snapshots and feature/label snapshots before developing forecasts. Candidate minimum is 12 weekly observations per assessed employee and enough positive and negative deadline outcomes across the account; 12 weeks alone does not establish reliability. Show insufficient data when conditions fail.

Evaluate with chronological train/validation/test splits and rolling-origin backtests, grouped by account/project to check transferability. Compare against simple overdue/base-rate and logistic-regression baselines. Report Brier score and calibration for risk; precision/recall at the intervention threshold; MAE and interval coverage for completion-date forecasts. Use leakage checks and subgroup checks across roles, task types and workload. Choose acceptance thresholds prospectively with management; no unvalidated numerical accuracy promise is made.

Rollout requires better-than-baseline held-out performance, reasonable calibration, clear explanations, drift monitoring, a rollback option and human review. Risk alerts should propose support or reprioritization. Never label employees as low performers using a forecast alone. No trained model or predictive probability is enabled in version 0.3.

## Implemented NLP-assisted policy system (v0.7)
Admins publish an account policy with weights summing to 100, NLP influence λ from 0–0.25, and minimum evidence thresholds at least five. Publishing creates a new immutable version and changes the active account pointer. Account policy versions are shown in Scoring policies; no edit/delete routes exist.

Admins freeze acceptance and documentation criteria on backlog/assigned tasks, binding them to a policy version and complexity before work starts. The UI uses equal checklist weights; the API supports explicit positive weights per item. Checklist criteria cannot be modified after freezing. Existing tasks without a rubric retain legacy manager-reviewed quality; task criteria must not be retrofitted after work starts.

Staff submit evidence as text or artifact references; Gazal does not fetch or inspect external artifact URLs. Lexical NLP tokenizes English-like words, removes a small stopword set and suggests passages by requirement-token overlap. It is an evidence retrieval baseline, not a language model, semantic entailment model or verification engine. Task descriptions and evidence are treated as data; no external AI provider receives them in this release.

The administrator verifies correctness c, acceptance aH, validation v and documentation dH on 0–1 scales, then confirms each checklist item as unmet (0), partial (0.5) or satisfied (1), with evidence references when evidence is available. NLP-assisted checklist scores are weighted reviewer-confirmed coverage, not automatically generated quality labels. Unsupported claims must be rated zero. The assessment stores inputs, derived values, reviewer and bound policy. Saving it approves the submitted task. The legacy approval route cannot bypass a frozen rubric.

q = 100 [0.40c + 0.30((1−λ)aH + λaN) + 0.20v + 0.10((1−λ)dH + λdN)].
aN and dN are weighted confirmed checklist coverage. λ is zero without evidence and otherwise the bound policy's value. With default overall weights and λ=.25, NLP-assisted coverage contributes at most four points to the final employee score. Changing overall quality weight changes that upper bound to quality_weight × .40 × λ.

Task quality uses its frozen policy version. Employee aggregate weights use the currently active account policy, explicitly identified in the API output; publishing a policy can therefore change current aggregate scores. Manually captured snapshots preserve results and policy identifiers and are append-only through the API. Snapshot capture is not automatically scheduled, and repeated captures on one date do not constitute separate weeks of historical evidence. No predictive model is enabled.
