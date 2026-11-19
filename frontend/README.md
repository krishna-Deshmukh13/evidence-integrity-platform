# Frontend scaffold (React 18 + TypeScript + Vite + Tailwind v4)

Run: `npm install` then `npm run build` (type-checks + builds). `npm run dev` needs the backend on :8000 (proxy `/api`).
**You do not need the backend to do your part. Verify with `npm run build` only.**

## File ownership (never edit files you do not own; this is how 5 separate zips merge with zero conflicts)
| Owner | Files |
|---|---|
| SHARED, never edit | `src/lib/*`, `src/components/{ui,ScoreDial,Layout,Placeholder}.tsx`, `src/viewers/Viewer.tsx`, `src/pages/{Login,NotFound}.tsx`, `src/{App,main}.tsx`, `src/index.css`, config files |
| Part 1 | `pages/{Dashboard,Cases,Case}.tsx` + new files in `src/components/case/` |
| Part 2 | `pages/Evidence.tsx` + new files in `src/components/evidence/` |
| Part 3 | `viewers/{ImageViewer,VideoViewer,AudioViewer,PdfViewer,DocxViewer}.tsx` + new files in `src/viewers/parts/` |
| Part 4 | `pages/{Search,Compare}.tsx` + new files in `src/components/search/` |
| Part 5 | `pages/{Activity,Users,HowItWorks}.tsx`, `components/GlobalShortcuts.tsx` + new files in `src/components/misc/` |

Need a helper that does not exist? Write it inside your own folder. Replace a placeholder file completely; keep its default export and props.

## Conventions
* Imports: `@/` = `src/`. Data: `api.*` from `@/lib/api` (typed with `@/lib/types`); hooks `useApi(fn, deps, {shouldPoll})` and `useDebounced` from `@/lib/hooks`; current user and roles: `useAuth()` returns `{user, can("investigator"), signOut}`.
* UI: use only the kit in `@/components/ui` (Button, Card, CardHeader, Badge, ScoreChip, VerdictText, Tabs, Segmented, Modal, ConfirmModal, Input/Select/Textarea/Field, Progress, Spinner, Loading, ErrorBox, Empty, PageHeader, Stat, Kbd, Mono, useToast) and `ScoreDial`. Icons: `@phosphor-icons/react`. Colours ONLY via token classes: `bg-surface bg-surface2 bg-bg border-line text-ink text-muted text-accent text-good text-warn text-bad bg-good-soft bg-warn-soft bg-bad-soft bg-accent-soft` (they switch for dark mode). No other UI or chart libraries: draw charts with plain SVG/divs. Must work on phones (390px wide): wrap grids (`grid-cols-2 md:grid-cols-4`), no sideways page scroll, wide tables scroll inside `overflow-x-auto`.
* Formatting helpers: `@/lib/format` (bytes, dateTime, ago, mmss, shortHash, scoreTone, verdictTone, sevTone, REVIEW_LABEL, MEDIA_LABEL, CATEGORY_LABEL).
* Role gating (the server enforces it; the UI only hides buttons): viewer = read, search, compare, ask, verify, export; investigator = plus create case, upload, re-analyse, rewrite report, review/assign/tag/notes, activity log; admin = plus delete case/evidence, users.
* Direct URLs for `<img>`, `<video>`, `<audio>`, `<a>`: `api.url.file(id)`, `api.url.artifact(id, name)`, `api.url.reportPdf(id)`, `api.url.casePdf(id)`, `api.url.activityCsv()`.
* Polling: evidence with `status` queued or analyzing (or `report_busy`) must auto-refresh every ~1.8 s until finished (`useApi` with `shouldPoll`). Show `stage` + `progress`; queued shows "Queued, N ahead" from `queue_position`.

## Routes (links between parts)
`/` dashboard, `/cases`, `/cases/:id`, `/evidence/:id`, `/compare?a=<id>&b=<id>`, `/search?...`, `/activity`, `/users`, `/how-it-works`.
`/search` reads and writes URL query keys named exactly like `SearchParams` in types.ts (`q, media_type, verdict, review_status, case_id, category, check, assignee_id, min_score, max_score, date_from, date_to, sort`; multiple values comma-separated, e.g. `verdict=Likely manipulated,Needs review`). Every dashboard number links into a filtered `/search`.

## Data facts you need (more in comments in `src/lib/types.ts`)
* Artifact file names in `ev.artifacts`: images `original.jpg ela.png noise.png clone.png ai_heatmap.png`; audio `spectrogram.png`; video `frame_00.jpg ...` plus `audio_spectrogram.png` and `ai_heatmap.png`; PDF `page-1.png ...`.
* Image `Finding.location` regions are in ORIGINAL pixels; artifact images are scaled to `details.preview_size` (draw boxes with `x * preview_w / details.width`). PDF boxes are PDF points; page images are 1.6 px per point (`px = pt * 1.6`). Times are seconds.
* Severities: info = passed (green), low (grey), medium (amber), high (red). Score bands: 80+ Consistent, 50-79 Needs review, below 50 Likely manipulated.
