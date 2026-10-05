# Authenticated route reconnaissance

Status: PARTIAL — the reachable authenticated surface is understood for the visible offer-listing module, but there is only one confirmed user-accessible route. No final audit was started.

## Scope and safety

- Start and final route: `http://4.209.241.167/consultant/appels-offres`
- Authentication: validated before each fresh production context; no redirect to login occurred.
- Approved run-scoped dependency origins: `http://4.209.37.93/`, `https://fonts.googleapis.com/`, and `https://fonts.gstatic.com/`.
- No logout, upload, add, delete, form-submit, or unknown control was clicked.
- A previous bounded collector interaction was classified safe and produced no visible effect. A three-action read-only probe was not recorded because the local console encoding failed at report output, so its outcome is not used as evidence here.

## Confirmed route inventory

| Route | Discovery | Purpose | Authenticated | Rendered | Safe audit seed |
| --- | --- | --- | --- | --- | --- |
| `/consultant/appels-offres` | Root redirect and visible sidebar anchor | Offer/RFP listing, filtering, document-card actions, pagination | Yes | Yes | Yes |

Excluded equivalents: `/` redirects to `/consultant/appels-offres`; `/projects` and `/projects/` are API endpoints, not UI routes. No fragments, query variants, guessed routes, hidden administration routes, or build-only routes were enumerated.

## Visible interactive inventory

The production collector detected 40 clickables. The focused visible-element inventory found 52 relevant controls after including pagination and local state controls. It reclassifies the previously unknown controls without operating them.

| Control group | Element type / role | Count | Classification | Navigation evidence | Action |
| --- | --- | ---: | --- | --- | --- |
| `Appels d'offres` | anchor | 1 | SAFE_NAVIGATION | Exact same-application href to the confirmed route | Not clicked; it is the current route |
| `Déconnexion` | button | 1 | LOGOUT | None | Excluded |
| Sort buttons: `Tout`, `Nom`, `Statut` | button | 3 | SAFE_STATE_CHANGE | Listing presentation only | Not clicked |
| Status filters: all, success, failed, pending, processing, ignored | button | 6 | SAFE_STATE_CHANGE | Listing state only | Not clicked |
| Read-only card actions: documents required, AI analysis, matching results | button | 15 | SAFE_STATE_CHANGE | View-oriented labels; no href | Not used as route evidence |
| Pagination: previous, pages 1–19, next | button | 21 | SAFE_STATE_CHANGE | Listing page state only | Not clicked |
| Delete actions | button | 5 | POTENTIALLY_DESTRUCTIVE | None | Excluded |
| Upload/add attachment zones | upload/dropzone UI | visible | POTENTIALLY_DESTRUCTIVE | None | Excluded |
| Profile/account display | non-link UI | 1 | UNKNOWN | No visible href or role | Not clicked |

After this contextual classification, there are 1 safe navigation control, 45 safe state-change controls, 5 potentially destructive controls, 1 logout control, and 1 non-interactive/unknown profile surface. File names and user-specific accessible labels are intentionally omitted from this artifact.

## Rendering and network evidence

- Meaningful DOM: 9 body children, 1 link, 51 buttons, 1 `nav`, 1 `aside`; no dialog, table, or form was present on the loaded listing state.
- First-party API: `/auth/me` returned 200; `/projects` redirected to `/projects/` then returned 200; `/auth/permissions` and `/rfps/` returned 200.
- Font resources: `fonts.googleapis.com` returned 200 and subsequently loaded `fonts.gstatic.com` font files with 200 responses. The approved-font screenshot shows the application with its intended font styling.
- No failed application requests occurred during the font-enabled inventory run.
- Lighthouse remains `collection_failed`. It is not used as a performance measurement and did not block this reconnaissance.

## Coverage risks and recommendation

The visible page is safe to seed for a full audit, but route coverage is not yet sufficient for a broad authenticated acceptance audit: the sidebar exposes only the current route, the crawler found no additional route-bearing controls, and profile/detail views were not visible as links. Mobile evidence also shows narrow-layout overflow in card actions.

Recommended seed list: `/consultant/appels-offres` only. Obtain additional user-visible route links or an authorized navigation path before treating the final audit as representative of other application modules.
