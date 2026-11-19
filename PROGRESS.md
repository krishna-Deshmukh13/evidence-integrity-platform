# Evidence Integrity Platform — Implementation Progress

> Tracking implementation progress across all feature groups. Each task is verified with automated tests and committed upon completion.

---

## Group A: Dashboard Upgrade
- [x] **A1. Backend (`routes/insights.py`)**
  - Verdict counts by media type
  - Score distribution in bins with bands: 0–49, 50–79, 80–100
  - Top findings (most frequent check names with counts)
  - Custody health (`chains_intact`, `chains_broken`, `last_checked_at`) + `POST /api/custody/verify-all` (Investigator & Admin)
  - Live queue (`current_file`, `stage`, `progress`, `waiting_count`, `report_model_status`)
  - Needs attention (failed analyses, flagged & unreviewed > 3 days, score < 50 with no assignee)
  - Per-case summary (file count, counts per verdict)
- [x] **A2. Frontend (`Dashboard.tsx` & Navigation)**
  - Greeting fix (skip titles like "Insp.", display real first name)
  - Replace empty Verdicts card with donut chart + media-type breakdown
  - Score distribution count labels & band markers
  - Custody health widget with "Verify all" action
  - Live analysis queue widget (polls while active, stops when idle)
  - Needs attention widget
  - Top findings bar chart
  - Case cards with mini risk bars
  - Reorder: "Highest risk" directly under stat tiles
  - Link all numbers/cards to filtered Search or page
  - Top bar model label: "Template reports (no model connected)"

---

## Group B: Case Intelligence
- [x] **B1. Case Timeline**
  - Backend: Timeline endpoint aggregating EXIF capture/modified, PDF dates, DOCX dates, video creation, upload time, custody events
  - Flag chronological contradictions (modified before created, captured after upload, future dates)
  - Frontend: "Timeline" tab on Case page linking flags to files
- [x] **B2. Evidence Graph**
  - Backend: Graph endpoint linking files by SHA-256, perceptual hash, software, camera model, author, GPS (<100m)
  - Frontend: Interactive SVG "Graph" tab on Case page & cross-case option on Search page
- [x] **B3. GPS View**
  - Coordinate plot / map on Metadata tab and Case page
  - Flag files > 50 km from other case files
- [x] **B4. Case Summary**
  - Case-level LLM report generation using existing LLM adapter with template fallback
  - Structured prompt with limitations section, author model record, and inclusion in Case bundle PDF
- [x] **B5. Score Sensitivity ("What would change the score")**
  - Deterministic recalculation showing points gained and verdict band shift if finding cleared
  - Display on Evidence detail page
- [x] **B6. Known-Manipulated List**
  - Known-manipulated registry table (SHA-256, perceptual hash, reason)
  - Matching new uploads flagged with info finding and custody note

---

## Group C: Legal and Provenance
- [x] **C1. Cryptographically Signed PDFs**
  - Local self-signed X.509 keypair generation stored outside uploads (`storage/keys/`)
  - PDF signing for per-file, case bundle, and Section 63 exports with visible signer fingerprint
- [x] **C2. Report Verification & Public Portal**
  - Report registry table (`exported_reports`) with SHA-256 and document verification token
  - Verification block with QR code on final page of all exported reports
  - Public `/verify` endpoint and page exposing no evidence content, filenames, or scores
- [x] **C3. Custody Chain Anchoring**
  - Signed JSON custody anchor export with all chain head hashes and timestamps
  - Verification endpoint and UI against uploaded anchor JSON with signature validation and chain traversal; graceful fallback for RFC 3161
- [x] **C4. Section 63 BSA 2023 Certificate**
  - Formal draft certificate under Section 63 of Bharatiya Sakshya Adhiniyam, 2023
  - Pre-filled evidence metadata, SHA-256 digest, custody summary, and declarant blanks
  - Export logged to immutable custody chain and activity log
- [x] **C5. Multi-Language Reports (Hindi & Marathi)**
  - Localized report template headers, section labels, and statutory declarations for Hindi (`hi`) and Marathi (`mr`)
  - Full Unicode font rendering using Windows Nirmala UI / FreeType fallback

---

## Group D: Research and Evaluation
- [x] **D1. Evaluation Framework (`backend/scripts/evaluate.py`)**
  - Benchmark script evaluating real analyzers on labelled dataset folders
  - Metrics: Precision, Recall, Specificity, F1, ROC-AUC, FPR, confusion matrix, and PNG plots
  - Printed directory layout instructions for CASIA v2, Columbia, FaceForensics++, ASVspoof
  - `--demo` mode runnable out-of-the-box on synthetic benchmark
- [x] **D2. Robustness Benchmark (`backend/scripts/robustness.py`)**
  - Forensic laundering perturbations: JPEG recompression (Q90, Q70, Q50), resizing (75%, 50%), screenshot-like PNG capture, and Gaussian noise
  - Generates `robustness_table.csv`, degradation line chart, and check survival heatmap
- [x] **D3. Machine Learning Fusion (`backend/scripts/ml_fusion.py`)**
  - Logistic Regression & Gradient Boosting models trained on findings features with cross-validation
  - Feature ablation table measuring individual check AUC contributions
  - Runtime fusion model exporting optional "ML-assisted confidence" beside deterministic forensic score
- [x] **D4. Examiner Feedback Loop**
  - Confirm / Reject buttons on findings for Investigators & Admins in UI
  - Feedback database logging, custody note generation, and CSV export for model retraining

---

## Group E: Engineering
- [x] **E1. Per-Case Access Control**
  - `case_members` table and role enforcement across all routes, insights, search, case intelligence, exports, and direct file downloads
  - Admin case membership management tab (`CaseMembersTab.tsx`) with instant reactivity and activity logging
  - Seamless fallback preserving unrestricted visibility for Platform Administrators
- [x] **E2. TOTP Two-Factor Authentication**
  - RFC 6238 TOTP enrolment via `pyotp` and QR code generation (`qrcode`) with base64 PNG data URIs
  - 8 one-time cryptographic recovery codes with SHA-256 hash storage and single-use consumption
  - Mandatory 2FA requirement for Admin and Investigator roles, optional for Viewer
  - Admin 2FA reset capability via `POST /api/users/{user_id}/reset-2fa` for locked accounts
  - Two-step sign-in prompt in `Login.tsx` and user security modal `TwoFactorModal.tsx`
- [x] **E3. Containerization & CI/CD**
  - Production-ready multi-stage `Dockerfile` (Node 20 frontend build + Python 3.11-slim CPU runtime) with ffmpeg, OpenCV, and static SPA serving
  - `docker-compose.yml` with persistent volume mount for SQLite database, cryptographic keypair, and uploads
  - `.github/workflows/ci.yml` CI pipeline running full backend pytest suite and frontend typecheck/build on push

---

## Group F: Forensic Assistant Chatbot
- [x] **F1. Assistant Engine & Intent Routing (`backend/app/assistant.py`)**
  - Read-only global assistant with Python-based intent routing (no model-driven tool calling)
  - Small talk handler with contextual suggestions tailored to the current page
  - Structured evidence search with media type, verdict, score bound, case reference, and keyword filters returning structured result cards
  - Case overview & triage ("Which file should I check first?", case statistics, unreviewed files)
  - System-wide overview ("What needs my attention?", pending urgent items, repository metrics)
  - Forensic score & finding explanations (category penalty breakdowns, spatial edit coordinate locations)
  - Prohibited phrase sanitizer: strictly avoids "is fake", "is authentic", "is genuine", and legal conclusions
  - Injection defense: Treats filenames, metadata, notes, and document text as untrusted data
  - Strict access control & case isolation: Non-admins cannot search or see files outside their assigned cases
  - Private per-user chat threads with history retrieval and clear endpoints (`POST /api/assistant/clear`)
- [x] **F2. Built-in Forensic Glossary (`backend/app/assistant_glossary.py`)**
  - Offline definitions for ELA, clone detection, noise analysis, SHA-256, pHash, EXIF, Grad-CAM, chain of custody, synthetic voice spectrograms, face deepfakes, and Section 63 BSA 2023
- [x] **F3. Assistant Frontend Widget (`frontend/src/components/assistant/AssistantWidget.tsx`)**
  - 48px round floating accent launcher button at bottom right with tooltip "Ask the assistant (A)"
  - Keyboard shortcut 'a' toggles side panel (respects typing inputs and Esc to close)
  - 350px slide-in side drawer, responsive full-screen on mobile (<640px)
  - Contextual header displaying current page ("On: Dashboard", "On: Case #...", "On: File #...") with Clear thread action
  - Rich chat stream with left/right bubbles, source badge pills ("Built-in templates", "Built-in glossary", LLM model name), and provenance notes ("Based on: ...")
  - Interactive clickable evidence result cards linking directly to the forensics viewer
  - Live typing indicator ("Looking through your evidence...")
  - Route-aware suggested questions chips above input for instant one-click prompts
  - Documented in "How it works" (`docs.tsx`) and keyboard shortcuts modal (`GlobalShortcuts.tsx`)
