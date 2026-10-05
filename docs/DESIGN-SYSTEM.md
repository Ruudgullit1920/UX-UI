# Design System

## Visual design pass 3

The current application uses solid content surfaces and treats translucency as a functional material. The canvas is #f5f5f7 in light mode and #0b0b0d in dark mode. Reading surfaces are #ffffff / #1c1c1e, with secondary surfaces #f8f8fa / #242426. Accent and keyboard focus use #0066cc in light mode and #0a84ff in dark mode.

`GlassSurface` supplies the translucent fill, border, highlight, shadow and blur for the floating application toolbar and contextual review action strip. It is not used for findings, evidence, forms, charts, or report content. Reduced-transparency and increased-contrast preferences replace it with an opaque elevated surface.

The configuration page presents source choices as one shared tray. Its evidence lens combines a blue tint, inset ring, checkmark and short lift to identify the active source without relying on color alone. The setup fields remain content on the canvas instead of appearing in a large enclosing card. Compact controls use 10/14px radii; content uses 18/26px radii; primary actions use a pill radius.

Interaction timing is 90ms for press, 140ms for hover, 220ms for selection, and 360ms for configuration entry. Motion explains a state change and is removed for `prefers-reduced-motion`. The toolbar remains independently floating while the page scrolls and its native appearance selector remains visible at every supported width.

**Implemented:** 2026-09-25 · Application only; generated reports retain their own styles.

## Point of view

A specialist should understand a measurement before trusting a recommendation. The signature is a dimension ledger pairing score and measurement coverage, followed by a finding browser where captured evidence leads the reading order. Content provides visual richness; there is no decorative imagery, gradient dashboard or KPI-card grid.

Apple Design skill improvement guidance informs hierarchy, progressive disclosure, predictable feedback and adaptable split views. This remains a web application with native HTML controls, authored SVG icons and browser conventions. The user-requested appearance selector is retained; Apple fonts, symbols and platform chrome are not copied.

## Tokens and type

Semantic colors live in tokens.css, including independent dark luminance layers. Contrast below is calculated against the opaque content surface, not estimated from screenshots.

| Role | Light | Contrast on #ffffff | Dark | Contrast on #1d242e |
| --- | --- | --- | --- | --- |
| Content | #20252c | 15.41:1 | #f0f2f5 | 13.93:1 |
| Secondary text | #5e6875 | 5.66:1 | #aeb7c4 | 7.72:1 |
| Action/focus | #245acc | 6.16:1 | #a5c1ff | 8.68:1 |
| Error/high severity | #aa3640 | 6.34:1 | #ffb0b7 | 9.04:1 |
| Warning/medium severity | #80531d | 6.62:1 | #e5c48d | 9.38:1 |

Light layers: #f6f7f9 page, #ffffff reading surface, #f3f5f7 navigation/subtle surface. Dark layers: #12161c page, #1d242e reading surface, #283240 navigation/subtle surface. Status fills have separate tokens and text labels.

The native system font stack downloads no fonts. Body/evidence is 1rem (16px default), evidence line-height 1.75, metadata .8125rem, section titles 1.25rem, selected finding titles 1.5rem and audit titles a 1.65–2.15rem clamp. Short machine IDs/data use the system monospace stack. Reading passages are limited to about 65–70ch.

Spacing uses 4/8/12/16/24/32/48/64px. Controls use 8px corners, workspace 12px, setup surface 20px. Controls are at least 44px high; fields 46px. Borders organize data and selection; opaque surfaces carry content. Blur is limited to the top bar and sticky review actions, with an opaque reduced-transparency fallback.

## Layout and interaction

The shell allows 1,600px of workspace; setup remains 1,080px. Global navigation sits above local audit tabs. Overview places the dimension ledger beside findings/review distributions; below 900px these stack. Dimension rows reflow at compact widths without shrinking evidence type.

Regular:
```text
Audit identity                         Report / source artifact
Overview | Findings | Review                         Revision state
Findings + search     | Selected finding
Real-field filters   | Captured evidence / provenance
Selected list row    | Machine assessment / review inspector
                     | Next review action + draft state
```

Compact:
```text
Audit identity / outputs
Overview | Findings | Review
Findings list → selected finding
               ← Back to findings
               Evidence → review
               Sticky next action
```

At 768px and above the two reading panes have bounded independent scrolling. Below 768px a single drill-in task fills the width. At 375px source cards form a two-by-two grid and fields stack. Ultrawide screens expand work surfaces while preserving text line limits.

Local tab transitions preserve the browser state. Selecting a different finding resets its reading position. Lists render 25 findings at a time. Sticky review feedback identifies the failed action beside its next action. Optional edits and history use native disclosures.

Motion uses 160ms feedback and 240ms disclosure entry. No orchestrated animation is needed for evidence review. Reduced motion disables transitions and indeterminate-bar animation; real stage text remains.

## Component ownership

| Component | Responsibility |
| --- | --- |
| App / AppShell | Current workspace, draft protection, global navigation, theme |
| AuditForm / source components | Compact source configuration, upload/discovery |
| useAuditJob / AuditWorkspace | Polling, cancellation, lifecycle, report loading |
| AuditOverview | Actual score/coverage rows, findings distribution, collection scope |
| FindingBrowser / EvidencePanel | Search/filter/selection, split/drill-in navigation, protected image/provenance |
| GuidedFindingEditor | Schema-aligned human review fields |
| ReviewPanel / useReview / reviewModel | Local sections, authoritative revision state, action ownership, conflicts, validation |
| RevisionHistory | On-demand saved revisions and immutable preview |
| ProtectedResource / api/artifacts | Protected output opening and bounded artifact paths |

Plain React and CSS implement the workspace. No UI, visualization, icon or animation dependency was added.

## Design review references

The installed apple-design references were consulted for principles, accessibility, layout, typography, color, dark mode, materials/Liquid Glass, motion, controls, navigation, loading/feedback, writing and AI/ML transparency.

Applied examples: layout.md › Visual hierarchy, “Use progressive disclosure”; split-views.md › Best practices, “persistently highlight the current selection”; materials.md › Liquid Glass, “Don’t use Liquid Glass in the content layer”; feedback.md › Best practices, “integrating status feedback into your interface”; generative-ai.md › Transparency, “Communicate where your app uses AI.” These are translated into web behavior rather than literal macOS imitation.
