# UX Specification

**Implemented:** 2026-09-25 · React/Vite application
Related: [Product](PRODUCT-SPECIFICATION.md), [Design system](DESIGN-SYSTEM.md), [Accessibility](ACCESSIBILITY.md), [API](API-SPECIFICATION.md).

## Shell and creation

Global navigation contains New audit and, once a job exists, Current audit. System/Light/Dark appearance persists locally. There is no invented audit-history page. Switching views preserves the current job, filters, selection and review draft in memory. Reload does not restore them. Leaving with a draft uses the browser warning; replacing it asks for confirmation before creating the next job.

New audit uses a compact heading and four native radio source cards. Website requires a public HTTP(S) URL; detailed mode appears under Advanced only when capabilities explicitly enables it. Screenshots accept the existing upload flow, filename/removal list, optional name and screen type. Mobile exposes its Appium/ADB requirement, discovery, package/activity and advanced connection settings. Figma requires its file URL and server-side access. The server retains all URL, upload and ownership validation. A running job must finish or be cancelled before another is created through this workspace.

## Audit workspace

The heading identifies source, target, creation time and actual job status. A completedAt timestamp is displayed only if supplied; updatedAt is labelled Last update inside details, never invented as a completion time. Queued/running views show real stage text, indeterminate progress, cancellation and live status. Polling continues after cancellation is requested until a terminal response arrives. Failed/cancelled/interrupted states offer recovery and real error details. Logs and full audit ID remain collapsed.

Completed jobs expose local Overview, Findings and Review tabs. Arrow keys, Home and End operate these tabs. Report and source-artifact buttons remain available above them. There is no separate Evidence tab: useful evidence is attached to findings and collection scope.

## Overview

The overview displays the source report's overall score, measurement coverage and summary. Dimension rows place scores beside independent coverage figures; opening a row reveals available confidence, rule counts, missing context and reasons. Null/unscored measurements display Not measured. Numeric zero remains zero. Model visual assessments are explicitly separate from measured scores. The five current methodology axes keep their actual report names; historical reports retain historical axes rather than being relabelled.

Findings counts and severity distributions use the canonical structured collection. Selecting a severity opens a filtered findings view. Review decision counts include the current local draft, labelled as such; no decision is a separate state. Collection scope uses reported page counts/coverage, captured-page lists, or Figma extraction counts where available. Collection coverage and measurement coverage have separate explanations. Absent report data produces an unavailable state rather than fabricated scores or totals.

## Findings and evidence

Desktop/tablet use two panes: findings navigation and a readable selected finding. Both have bounded scrolling at 768px and above. Below 768px the list drills into the selected detail, with an explicit Back to findings control and focus restoration.

Search covers titles, IDs, page URLs and evidence. Severity, dimension and review-decision filters appear only when their real values provide useful choices. Search/filters are omitted for one finding. Filters and selection survive local tab switches. Lists initially render 25 entries; Show next 25 reveals another batch, adequate for the tested 100-finding workload.

The detail separates observation/evidence, machine interpretation, impact, recommendation and human review. Available page URLs link out safely. The first supported screenshot reference is previewed using an authenticated blob; referenced paths must belong to this audit under existing protected artifact roots. Missing/unsupported images have an explicit fallback. Provenance exposes supplied evidence IDs, sources, selectors, criteria, measurement class, raw checks, visual region and limitations. The full original finding record remains available in a disclosure. No AI interpretation is labelled human-authored or raw measurement.

## Review inspector and actions

Review reuses the selected finding and its evidence. Machine interpretation is available in a disclosure. Decision, priority override and note are directly editable; reviewed recommendation and executive-priority suppression are disclosed on demand. Suppression requires a reason. Findings without stable IDs are read-only. Figma final issues are browsable but read-only because the revision/report adapter does not support that format. Draft Figma detection counts are identified separately and remain inspectable in the source artifact.

Edits follow the server schema: reviewDecision, priorityOverride, reviewNote, reviewedRecommendation, suppressed and suppressionReason. Text limits remain 1,200 characters, revision reason 1,000, and revisions contain 1–100 finding changes. Saving retains the full current set of review fields across findings.

The sticky action area shows draft/saved state, revision state and the primary next action:
- Edited draft → Save revision.
- Saved in_review → Validate revision.
- Validated/approved → Publish reviewed report.
- Approval is optional and secondary when validated.
- Publication success retains its returned link; new edits create another revision.

Each failure owns its action independently from pending state. Save/validate/approve/publish errors are specific and dismissible. Successful mutations and relevant draft changes clear obsolete errors. A failed read after a successful mutation is labelled as a refresh problem, preserving the successful mutation response. Brief success feedback expires after six seconds. Busy actions disable duplicate requests and editing.

HTTP 409 preserves drafts and blocks transitions. Reviewers refresh and explicitly choose the latest revision or retain their draft. A different current revision observed during a post-mutation refresh also blocks further writes. No silent merge or overwrite occurs. Publication refreshes revision and job state; responses from an unmounted workspace cannot replace a newer job.

History is collapsed by default, showing real revision state, current marker, timestamps and reason, with IDs and changes on demand. Publication invokes the existing immutable snapshot service; machine scores and evidence remain unchanged.

## Reports, contracts and limits

Authenticated report opening embeds local protected image/style/script assets into a sandboxed new-tab viewer, isolating report scripts from session credentials. Source JSON opens through the protected artifact endpoint. Popup, authorization and missing-resource errors are explicit.

No API routes or dependencies were added. The earlier source compatibility fixes support website deduplicated findings and screenshot/mobile report locations. Priorities without IDs are associated only through exact, unambiguous source matches.

Unavailable product information is not invented: audit history/trends, assignment and collaboration presence, persisted drafts, overall confidence for every source, universal completion timestamps, full capability/upload-limit discovery, cross-source measurement coverage and publication-history listings. A report's canonical finding count can differ from axis pain-point totals; the UI does not recompute the engine's deduplication. Figma drafts are not promoted to final findings.

## Verification

Browser tests run the built application against the authenticated local server with isolated test jobs. Audit execution and external publication are fixture-controlled; authentication, artifact ownership, revision transitions and storage use the real handlers. Tests cover creation, lifecycle, reports, evidence, filtering, 1/15/100 findings, review errors/conflicts, publication, responsive layout and keyboard interaction. See Accessibility for the verification boundary.
