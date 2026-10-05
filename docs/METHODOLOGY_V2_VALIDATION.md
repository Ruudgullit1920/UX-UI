# Methodology v2 Empirical Validation

## 1. Executive summary

This is an engineering validation study against `270d616`. Focused v2 tests pass, but calibration is unsafe: two distinct Accessibility logical defects can collapse into one score consequence when both use the broad `accessibility` dedupe family and no scorer-recognized target is present. This is a **DEDUPE_ERROR** and a stop condition; no mappings, weights, or production code were changed.

## 2. Validation scope

The study used the real `RULE_REGISTRY`, `axis_mapping`, `axis_rows`, `score_axis`, and `deduplicate_findings` functions in memory. It did not use live sites or mutate artifacts. Scope includes controlled attribution, eligibility, mode, family-dedupe, registry-composition, and no-evidence checks. Broader calibration/distribution conclusions stop at the confirmed correctness error.

## 3. Current scoring architecture

V2 resolves stable `Sheet:row` or `machine_criterion` keys to one typed primary axis. `SHEET_AXIS_MAP` is only used by an explicit v1 path. Numeric scoring includes applicable measured pass/fail rows; warnings, unknown, and unmeasured rows do not earn credit. `score_axis` groups rows by `scoreConsequenceId`/registry `dedupe_family` plus only `target`, `page_id`, or `pageId`.

## 4. Registry composition

| Axis | Registered | Score eligible | CORE | SUPPORTING | MINOR | A | B | C | D/E/F | Modes among scoreable entries |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Task | 44 | 44 | 5 | 39 | 0 | 0 | 5 | 39 | 0 | Website 44 |
| IA | 18 | 17 | 0 | 17 | 0 | 0 | 0 | 17 | 1 | Website 17 |
| Accessibility | 23 | 18 | 6 | 12 | 0 | 3 | 15 | 2 | 3 | Website 18 |
| UI | 40 | 35 | 0 | 35 | 0 | 0 | 0 | 35 | 5 | Website 35; Screenshot/Figma 17 |
| Content | 27 | 27 | 0 | 27 | 0 | 0 | 0 | 27 | 0 | Website 27 |

Task subfacets cover controls, continuity, forms, feedback, initiation, and runtime responsiveness. IA covers information scent and navigation structure. Accessibility covers contrast, semantics, forms, accessible names, and keyboard. UI is concentrated in visual hierarchy (21 of 35 scoreable entries). Content covers plain language, labels, instructions, and action wording.

## 5. Controlled scenario results

| Scenario | Expected primary axis | Actual primary axis | Expected score effect | Actual score effect | Unaffected axes preserved? | Dedupe correct? | Result |
|---|---|---|---|---|---|---|---|
| A clean measured audit | all | registry resolves one each | 100 where measured | consistent in simple rows | yes | n/a | provisional pass |
| B ambiguous action wording | Content | Content | Content only | Content only | yes | n/a | pass |
| C axe + custom + AI, same defect | Accessibility | Accessibility/report-only AI | one consequence | requires explicit shared logical ID | yes | pass with supplied ID |
| D control activation failure | Task | Task | Task only | Task only | yes | n/a | pass |
| E structural navigation | IA | IA | IA only | IA only | yes | n/a | pass |
| F visual hierarchy | UI | UI | UI only | UI only | yes | n/a | pass |
| G mixed form defects | Accessibility/Task/Content | distinct registry entries | one per defect | attribution correct | yes | see §14 | provisional |
| H LCP/FCP/TBT/Speed Index | Task | Task | one bounded consequence | one measured consequence | yes | pass |
| I AI-only finding | none | none | no numeric effect | no numeric mapping | yes | n/a | pass |
| J no measured evidence | none | none | null score | null/not scored | n/a | n/a | pass |

## 6. Single-rule sensitivity

With equal current weights, an ordinary independent one-rule failure has provisional delta `100 / scoreable entries`: Task 2.27 points, IA 5.88, Accessibility 5.56, UI 2.86, Content 3.70. These values are not calibration-ready because family dedupe changes effective denominators and the Accessibility defect in §14 invalidates exact comparison.

| Rule family example | Axis | Tier | Grade | Baseline | Single failure | Provisional delta | Concern |
|---|---|---|---:|---:|---:|---:|---|
| `Navigation:9` | IA | supporting | C | 100 | 94.12 | 5.88 | small rule population |
| `Content:4` | Content | supporting | C | 100 | 96.30 | 3.70 | none before calibration |
| `visual-hierarchy-reflects-priority` | UI | supporting | C | 100 | 97.14 | 2.86 | hierarchy concentration |
| `lcp` family | Task | core | B | 100 | bounded once | family-deduped | validate per page after fix |
| `axe:*`/`accessible_name` | Accessibility | core | A | invalid | invalid | invalid | over-broad family collision |

## 7. Axis sensitivity comparison

IA has the greatest provisional independent-rule impact because it has only 17 scoreable entries. UI has the lowest provisional independent-rule impact but is strongly concentrated in visual-hierarchy criteria. No inference about ideal weights is valid before the dedupe error is fixed.

## 8. Task validation

Task attribution for control behavior, feedback, form execution, recovery, continuity, and the performance family is singular. LCP/FCP/TBT/Speed Index produced one measured consequence in the controlled same-target family test. Task is not currently a Lighthouse-category score because `lighthouse_category` is report-only.

## 9. IA validation

Structural navigation resolves to IA; wording-only navigation resolves to Content; workflow progression resolves to Task; visual grouping resolves to UI. IA is a **COVERAGE_GAP** risk: deep findability, mental-model fit, and cross-route orientation are not objectively measured by this fixture study.

## 10. Accessibility validation

Axe, accessible-name, keyboard, contrast, and programmatic form-label entries resolve to Accessibility. AI-only observations do not map numerically. However, broad `accessibility` family grouping can merge distinct defects: this is a **DEDUPE_ERROR**, not a calibration question.

## 11. UI validation

Visual hierarchy and component appearance map to UI; wording and WCAG contrast do not. All UI scoreable entries are C-grade and 21/35 are visual hierarchy, creating a **COVERAGE_GAP / DISPLAY-INTERPRETATION_RISK** around heuristic concentration rather than a proven formula defect.

## 12. Content validation

Action wording, visible labels, instructions, and plain-language checks map only to Content. AI interpretation remains unscored. Audience fit, persuasion, and deep comprehension remain human-review boundaries.

## 13. Evidence-grade behavior

The registry permits only A/B/C grades to score. D entries are report-only, and E AI/VLM entries are report-only. No D/E/F exception was observed in the registry. This portion passes.

## 14. Deduplication validation

| Logical issue | Raw evidence count | Detector sources | Logical finding count | Numeric consequence count | Expected | Pass/fail |
|---|---:|---|---:|---:|---|---|
| Same unnamed button: axe + DOM + VLM with shared `logicalDefectId` | 3 | standards, deterministic, AI | 1 | 1 | one | pass |
| LCP/FCP/TBT/Speed Index for one target | 4 | performance metrics | 1 family | 1 | one | pass |
| Distinct axe name defect on page A + distinct custom name defect on page B | 2 | standards, deterministic | 2 intended | **1** | two | **fail** |

Proof: `axis_rows` assigned both rows `scoreConsequenceId='accessibility'`; although their `page_url` values differed, `score_axis` only reads `target`, `page_id`, or `pageId`. The controlled result was score `0.0`, measured count `1`, applicable count `1`; two independent rows should have retained two consequences (pass+fail would score 50).

## 15. Performance validation

The performance family behaves as intended in the controlled same-target test: four failed metrics yielded score 0 with measured count 1. Lighthouse aggregate is unmapped/report-only. This is provisional because actual performance rows are not emitted through the workbook fixture path.

## 16. Mode-specific behavior

| Axis | Website | Screenshot | Mobile | Figma |
|---|---|---|---|---|
| Task | 44 registry entries; runtime allowed | no runtime score | no native mappings | no runtime score |
| IA | 17 entries | none declared | none declared | none declared |
| Accessibility | 18 website entries | DOM/keyboard excluded | no native mappings | DOM/keyboard excluded |
| UI | 35 entries | 17 visual-hierarchy entries | no native mappings | 17 visual-hierarchy entries |
| Content | 27 website entries | none declared | none declared | none declared |

This confirms static modes do not score runtime performance, DOM semantics, keyboard operation, activation, or end-to-end completion. It also identifies mode coverage as incomplete rather than neutral.

## 17. Existing artifact/representative audit analysis

No representative stored artifact with a complete current v2 emitted-rule inventory was used. Live sites were intentionally not used. This is an **EXPECTED_LIMITATION**; controlled scenarios are sufficient to establish the dedupe stop condition.

## 18. Score distribution

No meaningful audit population was available after the stop condition. Any mean, median, standard deviation, floor/ceiling, or cross-audit comparison would be a misleading synthetic statistic.

## 19. Measurement coverage

`score_axis` keeps coverage separate from score and returns null when no applicable measured pass/fail evidence exists. The controlled no-evidence case passed. A future validation should surface examples such as high score with low coverage once correctness is restored.

## 20. Rule firing and registry coverage

Registry inventory: 166 entries, 141 score-eligible. The controlled fixture proves stable `Sheet:row` and partner `machine_criterion` lookups. It does not establish real-world firing frequency or prove every registry key has a current emitter; that remains a **COVERAGE_GAP**.

## 21. Unregistered findings

No artifact-derived unregistered-ID analysis was completed because calibration analysis stopped. The current safe v2 behavior for an unregistered key is reportable/unscored, which was confirmed in focused tests.

## 22. Critical blocker behavior

Existing `critical_eligible` remains independent of axis score arithmetic: it requires measured, applicable, verified critical failure. It affects the overall blocker flag, not unrelated axis attribution. No formula change was made.

## 23. Overall score behavior

`overall_score` averages only scored axes; null axes are excluded, not zeroed or neutralized. With very few scored axes an overall value can be interpretation-sensitive; this is a **DISPLAY/INTERPRETATION_RISK** for future policy, not a justification for calibration now.

## 24. Human-review boundary

Not objectively scoreable from current evidence: deep IA/mental-model fit, perceived trust, satisfaction, audience appropriateness, persuasion, deep comprehension, emotional response, complete accessibility conformance, and real-user task success.

## 25. Correctness issues

| Classification | Issue | Evidence | Required disposition |
|---|---|---|---|
| DEDUPE_ERROR | Broad Accessibility family collapses distinct defects when `target`/`pageId` is absent; `page_url` is ignored. | §14 in-memory production harness | fix and add regression before calibration |
| COVERAGE_GAP | Mobile has no native v2 mappings; screenshot/Figma support is narrow. | registry mode inventory | detector/mapping work later |
| COVERAGE_GAP | Real emitted-ID/firing-frequency analysis unavailable from fixtures. | §17/§20 | collect safe representative artifacts later |

## 26. Calibration questions

After the correctness fix: compare effective family denominators, assess IA small-population sensitivity, UI visual-hierarchy concentration, Task performance activation frequency, and display treatment for low-coverage scores. Do not choose coefficients from this study.

## 27. Axis readiness

| Axis | Correct mapping? | Adequate dedupe? | Evidence quality | Coverage | Score sensitivity | Primary concern | Status |
|---|---|---|---|---|---|---|---|
| Task | yes | provisional | B/C | website only | bounded performance family | no representative activation data | NEEDS_DETECTOR_WORK_FIRST |
| IA | yes | n/a | C | weak | high per rule | limited IA evidence | NEEDS_DETECTOR_WORK_FIRST |
| Accessibility | yes | **no** | A/B/C | website only | invalid pending fix | broad-family collision | NEEDS_MAPPING_FIXES_FIRST |
| UI | yes | n/a | C | visual modes partial | low per rule | hierarchy concentration | NEEDS_DETECTOR_WORK_FIRST |
| Content | yes | n/a | C | website only | moderate | no real firing sample | NEEDS_DETECTOR_WORK_FIRST |

## 28. Recommended next actions

1. Correct the dedupe key so distinct rule/target/page defects do not share a score consequence, while axe/custom/AI corroboration of the same defect still does.
2. Add regression coverage for two distinct Accessibility and two distinct performance-family defects on the same and different pages.
3. Re-run this study on controlled and safely copied representative artifacts, then assess calibration only after correctness is green.
4. Do not change mappings, weights, tiers, detector behavior, definitions, or score thresholds as part of this validation study.
