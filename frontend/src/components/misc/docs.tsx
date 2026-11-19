import type { ReactNode } from "react";
import { Card } from "@/components/ui";

export type Sec = { id: string; title: string; body: ReactNode };
const P = ({ children }: { children: ReactNode }) => <p className="mb-3 leading-relaxed">{children}</p>;
const UL = ({ items }: { items: ReactNode[] }) => <ul className="mb-3 list-disc space-y-1.5 pl-5">{items.map((i, n) => <li key={n}>{i}</li>)}</ul>;
const Code = ({ children }: { children: ReactNode }) => <code className="rounded bg-surface2 px-1 py-0.5 font-mono text-xs">{children}</code>;
const Table = ({ head, rows }: { head: string[]; rows: ReactNode[][] }) => (
  <div className="mb-3 overflow-x-auto rounded-lg border border-line">
    <table className="w-full text-left">
      <thead className="bg-surface2 text-xs text-muted"><tr>{head.map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
      <tbody className="divide-y divide-line">{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className="px-3 py-2 align-top">{c}</td>)}</tr>)}</tbody>
    </table>
  </div>
);

export const SECTIONS: Sec[] = [
  { id: "what", title: "What this is", body: <>
    <P>A web app that checks whether photos, videos, audio, PDF and Word files were edited, forged or AI-generated, and keeps a tamper-evident chain of custody for every file.</P>
    <P>It gives <b>technical indicators, not legal proof</b>. An examiner should always review the findings.</P></> },
  { id: "score", title: "How the score works", body: <>
    <P>Every file starts at 100. Each finding carries a penalty. Within a category the penalties are added and limited by that category's cap, then all categories are subtracted: <Code>100 - sum over categories of min(sum of penalties, cap)</Code>.</P>
    <Table head={["Severity", "Penalty"]} rows={[["High", "26"], ["Medium", "14"], ["Low", "6"], ["Passed", "0"]]} />
    <P>Strong evidence, such as an AI detector at 95%, carries a fixed larger penalty.</P>
    <Table head={["Category", "Cap"]} rows={[["Metadata", "30"], ["Pixel forensics", "40"], ["AI / deepfake", "55"], ["Document structure", "45"], ["Voice forensics", "55"], ["Container", "20"]]} />
    <Table head={["Score", "Verdict"]} rows={[["80-100", "Consistent"], ["50-79", "Needs review"], ["0-49", "Likely manipulated"]]} />
    <P><b>Worked example</b>, <Code>photo_tampered.jpg</Code>: clone detection -30, Photoshop tag -14, modified 2.7 days after capture -14. Total penalty 58, so 100 - 58 = <b>42</b> (Likely manipulated).</P></> },
  { id: "life", title: "Life of a file", body: <>
    <UL items={["Upload the file.", "SHA-256 hash is computed.", "Custody event \"Received\" is written.", "The file waits in the queue (one worker).", "Analysis runs; the file is re-hashed first.", "Score is calculated.", "Report is written: a template first, then the LLM.", "An examiner reviews the result."]} /></> },
  { id: "checks", title: "What is checked", body: <>
    <Table head={["Media", "Checks"]} rows={[
      ["Images", "EXIF metadata, EXIF thumbnail, error level analysis, noise consistency, clone detection (ORB), AI-generated image (SwinV2), face deepfake (ViT)"],
      ["Video", "Container tags, hard cuts, frozen frames, AI check on up to 20 frames, audio track"],
      ["Audio", "Synthetic voice (wav2vec2, 4-second windows), digital silence, bandwidth, tool tags"],
      ["PDF", "Incremental updates (%%EOF markers), signature coverage, producer/dates/XMP, font forensics, hidden text"],
      ["DOCX", "Tracked changes, author vs last saver, date order, editing sessions, mixed fonts"],
    ]} />
    <P>The AI models produce Grad-CAM heatmaps and run offline on CPU.</P></> },
  { id: "custody", title: "Chain of custody", body: <>
    <P>Each event stores who, when, a note, the file hash and the previous event's hash.</P>
    <P><Code>event_hash = SHA-256(evidence_id | seq | action | actor | time | file_hash | previous_event_hash | note)</Code></P>
    <P>Editing or deleting an old event breaks every later link. <b>Verify integrity</b> re-hashes the file and walks the chain.</P></> },
  { id: "dashboard", title: "Forensic Dashboard & Triage", body: <>
    <P>The forensic intelligence dashboard surfaces system-wide integrity metrics, analysis queues, and triage priorities in real time:</P>
    <UL items={[
      "Verdicts Donut & Media Distribution: Visual proportion of verdicts and breakdown across image, video, audio, and document formats.",
      "Score Bands: Triage breakdown across 0–49 (High risk), 50–79 (Needs review), and 80–100 (Consistent) with per-bin count indicators.",
      "Custody Health: Verifies that every evidence hash chain in the repository links unbroken back to genesis; includes one-click 'Verify all' for examiners.",
      "Live Analysis Queue: Non-blocking single-worker pipeline status polling active stages, progress, and waiting counts.",
      "Needs Attention: Proactively flags failed analyses, files unreviewed for >3 days, and high-risk files lacking an assigned investigator.",
      "Top Findings: Frequency analysis of manipulation check detections across all cases.",
    ]} /></> },
  { id: "case_intel", title: "Case Intelligence & Relationship Correlation", body: <>
    <P>Case intelligence aggregates cross-file forensic signals to uncover coordinated tampering or contradictions:</P>
    <UL items={[
      "Case Timeline: Chronological sequence of all EXIF capture dates, document timestamps, intake uploads, and custody events. Automatically flags contradictions (modified before created, captured after intake, future dates).",
      "Evidence Graph: Force-directed network diagram linking files by identical SHA-256, perceptual visual similarity (16-bit pHash), identical editing software, same camera make & model, document author, or GPS proximity (<100m).",
      "GPS Anomaly Detection: Plots embedded EXIF geographic coordinates and flags files located > 50 km from the case cluster.",
      "Score Sensitivity: Shows deterministically on each finding exactly how many points the integrity score would rise if cleared, and whether the verdict band would change.",
      "Known-Manipulated Registry: Cross-checks intake files against known synthetic or forged exemplars without score penalty changes.",
      "Case Summary: Synthesizes case findings using the pluggable LLM adapter with strict template fallback and legal disclaimers.",
    ]} /></> },
  { id: "provenance", title: "Legal Provenance, Signing & Section 63 BSA 2023", body: <>
    <P>Forensic reports and certificates adhere to legal evidence admissibility standards under Indian law and cryptographic verification protocols:</P>
    <UL items={[
      "Cryptographically Signed PDFs: All exported reports and certificates are digitally signed with an RSA-2048 X.509 keypair stored outside uploads, showing the signer fingerprint in the document footer.",
      "Public Verification Portal (/verify): Anyone can paste an exported report's SHA-256 hash or scan the QR code to verify issuance and date without disclosing evidence contents or investigative findings.",
      "Custody Anchoring: Produces a digitally signed JSON snapshot of every chain's head hash for external cold storage, verifiable against live state at any time with optional RFC 3161 timestamps.",
      "Section 63 Certificate (BSA 2023): Produces a formal draft certificate under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (replacing Section 65B IEA), pre-filled with SHA-256 digests, custody summary, and declarant blanks.",
      "Multi-Language Reports: Fixed report headings, tables, and statutory declarations are localized in English, Hindi (हिन्दी), and Marathi (मराठी) with Unicode font rendering.",
    ]} /></> },
  { id: "research", title: "Research, Evaluation & Learned Fusion", body: <>
    <P>Offline reproducible benchmarks evaluate analyzer reliability and model sensitivity across forensic datasets:</P>
    <UL items={[
      "Benchmark Framework (evaluate.py): Evaluates genuine and manipulated files across image (CASIA v2, Columbia), audio (ASVspoof), video (FaceForensics++), and document formats, computing Precision, Recall, F1, ROC-AUC, FPR, and Confusion Matrices.",
      "Robustness Degradation (robustness.py): Quantifies detector resilience against adversarial laundering including JPEG recompression (Q90, Q70, Q50), downscaling (75%, 50%), screenshot-like re-saves, and Gaussian noise.",
      "Learned Fusion & Ablation (ml_fusion.py): Trains cross-validated Logistic Regression and Gradient Boosting models on findings-derived penalties, compares AUC against the hand-tuned formula, and measures individual feature importance through systematic ablation.",
      "Examiner Feedback Loop: Investigators can Confirm or Reject individual findings to log audit trails and export retraining CSV data for model refinement.",
    ]} /></> },
  { id: "security", title: "Security & Access Control", body: <>
    <UL items={[
      "bcrypt password hashing with work factor 12",
      "15-minute JWT access tokens and rotating 7-day refresh tokens with reuse detection",
      "httpOnly, SameSite=Strict secure session cookies",
      "Login rate limiting and IP-based brute force throttling",
      "Roles Admin / Investigator / Viewer strictly enforced on the server for all endpoints",
      "Per-case access control: Non-admins only access cases they own or are assigned to as members",
      "TOTP two-factor authentication (RFC 6238) with QR code provisioning, manual secret, and hashed one-time recovery codes",
      "Admin 2FA reset capability for account recovery without breaking custody logs",
      "Immutable activity audit log tracking every view, export, verification, and membership change with client IP addresses"
    ]} /></> },
  { id: "engineering", title: "Engineering & Deployment", body: <>
    <P>The platform is architected for clean, reproducible on-premises and containerized deployment:</P>
    <UL items={[
      "Multi-stage Dockerfile: Builds React frontend using Node 20 and packages into a lean Python 3.11 CPU runtime image with ffmpeg and OpenCV.",
      "Docker Compose: One-command startup with persistent local volume for SQLite database, cryptographic keypair, and uploaded evidence.",
      "Automated CI/CD: GitHub Actions workflow running complete backend pytest suite and frontend typecheck/build on every push.",
      "Zero Cloud Dependencies: 100% offline CPU operation with zero paid API requirements.",
    ]} /></> },
  { id: "assistant", title: "Global Forensic Assistant", body: <>
    <P>A read-only conversational assistant integrated across the platform to accelerate evidence triage, case analysis, and terminology lookup:</P>
    <UL items={[
      "Plain-Language Evidence Search: Find files by media type, score, verdict, or case reference (e.g., 'Show likely manipulated PDFs from case CR-2013-0706') returning structured, clickable evidence cards.",
      "Case & System Triage: Answers queries like 'Which file should I check first?' or 'What needs my attention?' using recorded forensic metrics and status queues.",
      "Score & Finding Explanations: Explains why a file received a specific score, breaks down category point deductions, and details identified spatial edit coordinates.",
      "Built-in Forensic Glossary: Explains key forensic concepts (ELA, clone detection, noise analysis, SHA-256, pHash, EXIF, Grad-CAM, custody, spectrogram, deepfakes, Section 63 BSA 2023) without requiring an external model.",
      "Context-Aware & Privacy-Preserving: Automatically tracks the current page, case, or evidence ID. Strictly read-only, never outputs definitive legal conclusions, treats metadata as untrusted data, and respects per-case access isolation.",
    ]} /></> },
  { id: "limits", title: "Limitations", body: <>
    <UL items={[
      "A low score is an indicator, not proof.",
      "A high score does not prove authenticity.",
      "Detectors only know the generators they were trained on.",
      "Recompressed media loses metadata.",
      "There is one analysis worker (sequential queue processing to guarantee deterministic custody chains).",
    ]} /></> },
];

export const Section = ({ s }: { s: Sec }) => (
  <Card className="mb-4 scroll-mt-4 p-5"><section id={s.id}><h2 className="mb-3 text-lg font-semibold">{s.title}</h2>{s.body}</section></Card>
);
