"""Built-in forensic terminology glossary for the Evidence Integrity Platform assistant."""
import re
from typing import Optional, Tuple

GLOSSARY = {
    "ela": {
        "term": "Error Level Analysis (ELA)",
        "definition": (
            "Error Level Analysis (ELA) works by intentionally re-saving an image at a known quality level (typically 90%) "
            "and calculating the difference in JPEG compression error levels between the original and recompressed image. "
            "Areas of the image that were modified, spliced, or pasted from another source usually compress at a different rate, "
            "appearing significantly brighter in the ELA layer."
        ),
        "aliases": ["ela", "error level analysis", "error level", "compression error"]
    },
    "clone_detection": {
        "term": "Clone Detection (Copy-Move Forgery)",
        "definition": (
            "Clone detection identifies regions within the same image or frame that have been duplicated to cover up objects, "
            "replicate evidence, or duplicate crowds. The platform uses Oriented FAST and Rotated BRIEF (ORB) keypoint feature "
            "descriptors and density clustering to trace matching vector paths between duplicated regions."
        ),
        "aliases": ["clone", "clone detection", "copy-move", "copy move", "cloning", "cloned region", "duplicate region"]
    },
    "noise_analysis": {
        "term": "Noise Consistency Analysis",
        "definition": (
            "Every digital camera sensor imparts a subtle, uniform pattern of high-frequency noise across genuine photos. "
            "Noise analysis uses high-pass Laplacian filtering to measure noise variance across image grid blocks. If a spliced "
            "or inserted object has an inconsistent noise profile compared to surrounding pixels, it indicates image composition."
        ),
        "aliases": ["noise", "noise analysis", "noise consistency", "sensor noise", "laplacian"]
    },
    "sha256": {
        "term": "SHA-256 Hash",
        "definition": (
            "SHA-256 (Secure Hash Algorithm 256-bit) is a cryptographic hash function that produces a unique 64-character "
            "hexadecimal fingerprint for any digital file. If even a single byte, bit, or pixel is altered, the SHA-256 digest "
            "changes completely (avalanche effect), providing mathematical proof of data integrity."
        ),
        "aliases": ["sha256", "sha-256", "hash", "file hash", "cryptographic hash", "digest"]
    },
    "phash": {
        "term": "Perceptual Hash (pHash)",
        "definition": (
            "Unlike cryptographic hashes which change completely with a single bit difference, a perceptual hash (pHash) "
            "represents the visual structure of media. It uses the Discrete Cosine Transform (DCT) to generate a compact fingerprint. "
            "Files with a Hamming distance of 16 bits or fewer (≤25% difference) are flagged as visual duplicates or recompressed copies."
        ),
        "aliases": ["phash", "perceptual hash", "dct hash", "visual hash", "hamming distance"]
    },
    "exif": {
        "term": "EXIF Metadata",
        "definition": (
            "Exchangeable Image File Format (EXIF) is technical metadata automatically embedded in photos and video containers. "
            "It records hardware parameters (camera make, model, lens, shutter speed, ISO), capture timestamps, GPS coordinates, "
            "and software markers like Adobe Photoshop or GIMP that reveal editing history."
        ),
        "aliases": ["exif", "metadata", "exif data", "camera metadata", "creation date"]
    },
    "gradcam": {
        "term": "Grad-CAM (AI Heatmap)",
        "definition": (
            "Gradient-weighted Class Activation Mapping (Grad-CAM) visualizes which spatial areas of an image or video frame "
            "influenced the deep learning neural network (such as Swin Transformer V2 or Vision Transformer) to classify it as synthetic or deepfaked. "
            "Warm colors (red and yellow) indicate regions that triggered manipulation flags."
        ),
        "aliases": ["grad-cam", "gradcam", "ai heatmap", "heatmap", "class activation map"]
    },
    "custody": {
        "term": "Chain of Custody",
        "definition": (
            "The chain of custody is an immutable, chronologically ordered log tracking every intake, examination, export, and verification "
            "action performed on evidence. Each event includes sequence number, actor name, timestamp, current file hash, note, and is "
            "cryptographically bound to the previous event's hash, forming a tamper-evident audit trail."
        ),
        "aliases": ["custody", "chain of custody", "custody chain", "custody log", "audit trail"]
    },
    "spectrogram": {
        "term": "Audio Spectrogram Analysis",
        "definition": (
            "A spectrogram is a visual representation of the spectrum of acoustic frequencies in an audio signal as they vary with time. "
            "In forensic voice triage, spectrograms expose artificial high-frequency cutoffs, unnatural phase alignments, digital silence, "
            "and synthetic artifact signatures typical of text-to-speech (TTS) synthesis engines."
        ),
        "aliases": ["spectrogram", "audio forensics", "voice forensics", "frequency analysis"]
    },
    "deepfake": {
        "term": "Deepfake & Synthetic Media",
        "definition": (
            "Deepfakes and synthetic media refer to images, audio, or video created or altered through generative artificial intelligence, "
            "including diffusion models, GANs, facial reenactment, and neural voice cloning. The platform triages synthetic generation "
            "using fine-tuned SwinV2, ViT, and Wav2Vec2 models running completely offline."
        ),
        "aliases": ["deepfake", "deepfakes", "synthetic media", "synthetic voice", "ai generated", "ai generation", "voice clone"]
    },
    "section63": {
        "term": "Section 63 Certificate (BSA 2023)",
        "definition": (
            "Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (replacing Section 65B of the Indian Evidence Act, 1872) governs "
            "the legal admissibility of electronic records in Indian courts. It mandates certification identifying electronic records, "
            "describing computer device operations, and confirming integrity during production."
        ),
        "aliases": ["section 63", "section 63 bsa", "bsa 2023", "bharatiya sakshya adhiniyam", "65b", "section 65b", "legal certificate"]
    },
    "custody_anchor": {
        "term": "Custody Chain Anchor",
        "definition": (
            "A custody anchor is an exportable, digitally signed JSON snapshot capturing the head hash, timestamp, and sequence number "
            "of every chain on the platform. It can be stored offline or on external write-once storage to prove that the historical state "
            "of repository chains has not been rewritten or altered at any subsequent date."
        ),
        "aliases": ["anchor", "custody anchor", "chain anchor", "anchor json"]
    }
}


def lookup_term(query: str) -> Optional[Tuple[str, str]]:
    """Check if query is asking for a definition in the glossary.
    Returns (term_title, definition) if matched, else None."""
    q = query.strip().lower()

    # Pattern check: "what is X", "explain X", "tell me about X", "what does X mean", "define X"
    extract_patterns = [
        r"^(?:what\s+is|what's|whats)\s+(?:an?\s+|the\s+)?([a-z0-9_\-\s]+?)(?:\?|$)",
        r"^(?:explain|describe|define)\s+(?:an?\s+|the\s+)?([a-z0-9_\-\s]+?)(?:\?|$)",
        r"^tell\s+me\s+about\s+(?:an?\s+|the\s+)?([a-z0-9_\-\s]+?)(?:\?|$)",
        r"^what\s+does\s+(?:an?\s+|the\s+)?([a-z0-9_\-\s]+?)\s+mean(?:\?|$)",
        r"^meaning\s+of\s+([a-z0-9_\-\s]+?)(?:\?|$)",
        r"^([a-z0-9_\-]+)\s*\?$",
    ]

    target = None
    for p in extract_patterns:
        m = re.search(p, q)
        if m:
            target = m.group(1).strip()
            break

    if not target:
        # Check if query is short and matches a glossary term directly
        clean_q = re.sub(r"[^a-z0-9\s-]", "", q).strip()
        if len(clean_q.split()) <= 4:
            target = clean_q

    if not target:
        return None

    # Search glossary
    for key, item in GLOSSARY.items():
        for alias in item["aliases"]:
            if target == alias or target == alias.replace("-", " ") or target == alias.replace(" ", "-"):
                return item["term"], item["definition"]
            # Also check if alias is exact match inside target
            if re.search(r"\b" + re.escape(alias) + r"\b", target):
                return item["term"], item["definition"]

    return None
