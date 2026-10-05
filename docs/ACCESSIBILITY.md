# Accessibility

## Visual design pass 3

The floating toolbar's material has an opaque fallback for `prefers-reduced-transparency` and `prefers-contrast: more`. It does not place text or evidence on translucent cards. The source evidence lens provides a checkmark, radio state and focus indication in addition to its accent tint. The compact toolbar preserves a visible native appearance selector instead of hiding a focusable control.

The current semantic action colors are #0066cc on white in light mode and #0a84ff on #1c1c1e in dark mode; both meet the 4.5:1 AA normal-text threshold. Press, hover and selection motion is disabled for `prefers-reduced-motion`.

**Implemented:** 2026-09-25 · Application verification, not a conformance certification.
Related: [UX specification](UX-SPECIFICATION.md), [Design system](DESIGN-SYSTEM.md).

## Structure, navigation and focus

The document has an English language, header/navigation/main/footer landmarks, ordered headings and a skip link hidden until focused. The main target receives a visible keyboard focus outline. Source cards are native radios with arrow-key behavior and visible selected/focus states.

Local audit tabs expose tablist/tab/tabpanel relationships, selection and roving focus. Arrow Left/Right and Home/End select tabs. Findings use named buttons with aria-pressed selection; they are ordinary buttons, not an incomplete custom listbox. Search and filters use labelled native controls. On compact screens selecting a finding focuses its heading; Back to findings restores focus to its selected list button.

Controls retain visible three-pixel focus indicators, practical 44px targets, and native Enter/Space behavior. Disclosures provide built-in keyboard handling. Scrollable logs and raw evidence details are focusable. Browser-native confirmation handles possible draft loss; no custom modal or focus trap is introduced.

## Reading and appearance

Body and evidence text default to 16px; metadata to 13px. Reading lines are bounded; long URLs, source records and identifiers wrap. Semantic colors have independently reviewed light/dark variants. Scores, coverage, severity, selection and status are labelled, never communicated by color alone. See Design System for computed token contrast.

Reduced motion disables decorative transitions and progress animation. Reduced transparency uses opaque toolbar surfaces. Increased contrast strengthens separators and list boundaries. Captured evidence images retain their source colors because altering an audit screenshot could distort the evidence.

## Forms and state

Fields have persistent visible labels and associated helper text. Native URL/required validation applies at creation. Review uses the exact supported fields and server limits. Suppression requires a reason; errors name the missing information and appear in an alert region. Action errors identify save, validation, approval, publication or refresh separately and can be dismissed. Mutation success clears obsolete failures. Busy states disable duplicate submissions and review editing.

Live regions announce stage changes, terminal outcomes, finding counts, errors and review feedback. Unknown progress remains indeterminate without invented aria-valuenow. Unknown measurements remain Not measured rather than zero. Protected screenshot previews include descriptive alternate text tied to the finding; supporting observation/provenance stays textual. The protected report iframe has a title and isolated script context.

## Verification boundary

tests/test_frontend_browser.py runs the actual built app against authenticated local API handlers with deterministic test evidence and publication fixtures. It exercises keyboard audit creation, review actions, source radio arrows, local tab arrows/Home/End, skip-link focus, mobile drill-in focus restoration, native form controls, filter/search behavior, publication, error recovery and conflicts.

Responsive checks cover 375/768/1024/1280/1440/1728px for the overview and 375/768/1024/1440px for setup/review in both themes. Automated axe-core checks use WCAG 2 A/AA and 2.1 A/AA tags. Screenshots are inspected separately, including a second layout-polish pass. A 200% root-text test checks compact overview reflow. These checks do not establish WCAG conformance.

Screen-reader/browser combinations, Safari/iOS, Firefox, forced-colors behavior and a complete manual accessibility audit remain unverified. The browser is Chromium in this environment. Generated reports and audited target products are separate accessibility surfaces and are not certified by these application tests.
