import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { BookOpen, MagnifyingGlass, Tag } from "@phosphor-icons/react";
import { Card, CardHeader, Empty, cx } from "@/components/ui";

interface TermItem {
  term: string;
  category: "Cryptography" | "Image Forensics" | "Audio and Video" | "Documents" | "AI and Models" | "Platform";
  definition: string;
}

const GLOSSARY_TERMS: TermItem[] = [
  // 1. Cryptography
  { term: "SHA-256", category: "Cryptography", definition: "A cryptographic secure hash algorithm that outputs a unique 256-bit (64-character hex) digital fingerprint of any file. Even a single bit change in the file completely changes the hash." },
  { term: "Hash Chaining", category: "Cryptography", definition: "A mathematical ledger structure where each new custody event includes the cryptographic hash of the previous event, making historical tampering mathematically impossible to conceal." },
  { term: "Section 63 (BSA 2023)", category: "Cryptography", definition: "Section 63 of India's Bharatiya Sakshya Adhiniyam 2023 governing the legal admissibility of electronic evidence in courts, requiring proof of integrity, chain of custody, and digital hash certification." },
  { term: "Digital Signature", category: "Cryptography", definition: "An asymmetric cryptographic scheme using a private key to sign an evidence report or certificate, allowing anyone with the corresponding public key to verify authenticity and non-repudiation." },
  { term: "RSA-2048", category: "Cryptography", definition: "An asymmetric public-key cryptosystem with a 2048-bit key length used to legally sign forensic certificates and protect integrity anchors." },
  { term: "Custody Anchor", category: "Cryptography", definition: "A cryptographic checkpoint that freezes the Merkle root or top hash of the entire repository at a specific point in time to prevent post-facto ledger tampering." },
  { term: "Merkle Tree", category: "Cryptography", definition: "A hierarchical binary tree of cryptographic hashes where every parent node is the hash of its children, enabling rapid and secure verification of large volumes of evidence." },

  // 2. Image Forensics
  { term: "Error Level Analysis (ELA)", category: "Image Forensics", definition: "A forensic analysis method that re-compresses an image at a known JPEG quality level and subtracts it from the original to highlight regions saved with different compression histories, revealing localized edits." },
  { term: "Clone Detection (Copy-Move)", category: "Image Forensics", definition: "A computer vision technique using ORB or SIFT keypoint descriptors to identify identical or near-identical image patches that have been copied and pasted to hide or duplicate objects." },
  { term: "ORB Keypoints", category: "Image Forensics", definition: "Oriented FAST and Rotated BRIEF; a rotation-invariant, high-performance feature detector used to find and correlate matching vector patterns across image regions." },
  { term: "Sensor Pattern Noise (PRNU)", category: "Image Forensics", definition: "Photo-Response Non-Uniformity; microscopic sensor imperfections unique to a physical camera sensor that act like a digital fingerprint across all photographs taken with that device." },
  { term: "Noise Residual Analysis", category: "Image Forensics", definition: "Filtering out low-frequency visual content to isolate high-frequency sensor noise. Inconsistent noise levels across blocks indicate smoothing, filtering, or pasted foreign elements." },
  { term: "EXIF Metadata", category: "Image Forensics", definition: "Exchangeable Image File Format tags embedded in digital media files recording camera make, model, exposure settings, GPS coordinates, and creation/modification timestamps." },
  { term: "Quantization Table", category: "Image Forensics", definition: "The matrix used by JPEG compression algorithms to discard high-frequency visual data. Different image software (Photoshop, GIMP, iOS, Android) use distinct characteristic quantization tables." },

  // 3. Audio and Video
  { term: "Spectrogram", category: "Audio and Video", definition: "A visual representation of the spectrum of frequencies of a sound signal as they vary with time, vital for detecting voice synthesis and spliced audio." },
  { term: "Fast Fourier Transform (FFT)", category: "Audio and Video", definition: "A mathematical algorithm that converts audio wave signals from the time domain into frequency domain bins to analyze harmonic structure and synthetic artefacts." },
  { term: "Spectral Centroid", category: "Audio and Video", definition: "A metric indicating the center of mass of an audio spectrum, often associated with perceived sound brightness and used to identify unnatural acoustic shifts." },
  { term: "Pitch Contour", category: "Audio and Video", definition: "The curve of fundamental frequency variation over speech. Synthetic deepfake voices (TTS) often exhibit unnaturally flat or robotic pitch contours lacking micro-tremors." },
  { term: "Digital Silence", category: "Audio and Video", definition: "Sections of an audio recording with exactly zero amplitude values. Natural physical microphones always record room ambient noise; absolute zero silence indicates digital editing or splicing." },
  { term: "Temporal Video Splice", category: "Audio and Video", definition: "A sharp break in frame-to-frame pixel continuity where frames were cut or inserted, measured through sudden Euclidean frame difference spikes." },
  { term: "Dropped Frame Anomaly", category: "Audio and Video", definition: "Gaps in presentation timestamps (PTS) or discontinuous frame indices indicating deleted segments or recording interruptions in surveillance footage." },

  // 4. Documents
  { term: "Incremental Revision", category: "Documents", definition: "In PDF files, updates appended to the end of the file without overwriting original content. Incremental updates often reveal previous values of modified text or numbers." },
  { term: "Font Alteration", category: "Documents", definition: "The presence of differing embedded font subsets, character spacing, or glyph definitions within a single paragraph or table, indicating edited amounts or terms." },
  { term: "Metadata Inconsistency", category: "Documents", definition: "Contradictions between document creation software (e.g. Acrobat Distiller) and operating system file timestamps, or modify dates earlier than creation dates." },
  { term: "Hidden Text Stream", category: "Documents", definition: "Invisible OCR text or transparent text layers placed beneath scanned document images that differ from the visible rendered pixels." },

  // 5. AI and Models
  { term: "Deepfake Detection Heatmap", category: "AI and Models", definition: "A neural network probability map overlay that highlights localized pixel regions exhibiting synthetic diffusion or GAN generation patterns." },
  { term: "Multi-Modal Fusion Scoring", category: "AI and Models", definition: "An ensemble scoring model that aggregates independent evidence from metadata checks, pixel signal analysis, audio harmonics, and perceptual hashes into a single 0-100 integrity index." },
  { term: "Perceptual Hash (pHash)", category: "AI and Models", definition: "A fingerprint of multimedia content derived from visual features rather than raw bytes, allowing detection of cropped, resized, or recolored versions of the same file." },
  { term: "Hamming Distance", category: "AI and Models", definition: "The number of bit positions in which two binary perceptual hash strings differ. A low Hamming distance (e.g. ≤ 10 bits) indicates strong visual similarity." },
  { term: "Confidence Interval", category: "AI and Models", definition: "A statistical metric expressing the degree of certainty associated with an AI model's prediction of manipulation probability." },
  { term: "Local Inference Engine", category: "AI and Models", definition: "On-premise execution of computer vision and neural detection algorithms without sending confidential evidence data to third-party cloud servers." },

  // 6. Platform
  { term: "Chain of Custody", category: "Platform", definition: "The cradle-to-grave verifiable history of an electronic record detailing who accessed, examined, transferred, or modified the item, when, and with what authorization." },
  { term: "Case Bundle PDF", category: "Platform", definition: "A consolidated forensic report compiling all case evidence, individual scores, verified findings, examiner notes, and cryptographic certificates into a court-ready dossier." },
  { term: "Examiner Review Workflow", category: "Platform", definition: "The formal triage state of an evidence file: Not Reviewed, Flagged (High Risk), Under Review, or Cleared & Consistent." },
  { term: "Two-Factor Authentication (TOTP)", category: "Platform", definition: "Time-based One-Time Passwords adhering to RFC 6238 ensuring that administrative and investigative accounts require an authenticator code to prevent unauthorized access." },
  { term: "Tamper-Evident Ledger", category: "Platform", definition: "An append-only database table cryptographically enforced so that any modification to past rows breaks hash verification on subsequent rows." },
];

const CATEGORIES = ["All", "Cryptography", "Image Forensics", "Audio and Video", "Documents", "AI and Models", "Platform"] as const;

export default function GlossaryPage() {
  const [activeCategory, setActiveCategory] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedLetter, setSelectedLetter] = useState<string>("All");

  const letters = useMemo(() => {
    const s = new Set<string>();
    GLOSSARY_TERMS.forEach((t) => s.add(t.term[0].toUpperCase()));
    return ["All", ...Array.from(s).sort()];
  }, []);

  const filteredTerms = GLOSSARY_TERMS.filter((t) => {
    if (activeCategory !== "All" && t.category !== activeCategory) return false;
    if (selectedLetter !== "All" && !t.term.toUpperCase().startsWith(selectedLetter)) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return t.term.toLowerCase().includes(q) || t.definition.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">
            Knowledge Base & Terminology Standards
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-ink mt-1">
            Forensic Glossary & Terminology
          </h1>
        </div>

        <div className="relative">
          <MagnifyingGlass size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search forensic terms..."
            className="h-10 w-60 sm:w-72 rounded-full border border-line bg-surface pl-9 pr-4 text-xs font-medium outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all shadow-xs"
          />
        </div>
      </div>

      {/* Category Filter Tabs - Roomify Pill Style */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setActiveCategory(c)}
            className={cx(
              "rounded-full px-4 py-2 text-xs font-bold whitespace-nowrap transition-all shadow-2xs ",
              activeCategory === c
                ? "bg-[#0B0B12] text-white shadow-xs"
                : "border border-line bg-surface text-muted hover:text-ink hover:bg-surface2"
            )}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Alphabetical Jump Filter */}
      <div className="flex items-center gap-1 overflow-x-auto py-2 text-xs font-bold border-y border-line/60">
        <span className="text-muted text-[11px] mr-2 font-extrabold">A-Z:</span>
        {letters.map((l) => (
          <button
            key={l}
            onClick={() => setSelectedLetter(l)}
            className={cx(
              "size-7 grid place-items-center rounded-full transition-all text-xs font-bold",
              selectedLetter === l ? "bg-accent text-white shadow-xs" : "text-muted hover:text-ink hover:bg-surface2"
            )}
          >
            {l}
          </button>
        ))}
      </div>

      {/* Terms Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredTerms.length === 0 ? (
          <div className="col-span-2">
            <Empty title="No matching glossary terms found" />
          </div>
        ) : (
          filteredTerms.map((item, idx) => (
            <Card key={idx} className="p-5 space-y-2.5 rounded-[22px] card-bento transition-all hover:border-accent/40">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-extrabold text-sm text-ink">{item.term}</h3>
                <span className="rounded-full bg-[#EBEBFE] text-accent px-2.5 py-0.5 text-[10px] font-bold shrink-0">
                  {item.category}
                </span>
              </div>
              <p className="text-xs text-muted leading-relaxed font-medium">
                {item.definition}
              </p>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
