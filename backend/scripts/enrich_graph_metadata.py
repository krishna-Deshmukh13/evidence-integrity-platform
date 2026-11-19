"""Enrich database evidence with realistic camera, software, author, and hash cross-case links."""
import os
import sys
import json
import random
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("EI_STORAGE_DIR", str(backend_dir / "storage"))

from app.database import SessionLocal
from app.models import Evidence, Case
from app.routes.case_intel import get_cross_case_graph

def enrich_evidence_metadata():
    db = SessionLocal()
    evidence_items = db.query(Evidence).all()
    print(f"Total evidence items to enrich: {len(evidence_items)}")

    # Pools of realistic forensic signatures to create cross-case intelligence clusters
    CAMERAS = [
        {"Make": "Axis", "Model": "P1375 Network Camera"},
        {"Make": "Hikvision", "Model": "DS-2CD2385G1-I"},
        {"Make": "Axon", "Model": "Body 3 Enterprise"},
        {"Make": "Canon", "Model": "EOS 200D"},
        {"Make": "Sony", "Model": "Alpha A7S III"},
        {"Make": "FLIR", "Model": "SeaFLIR 280-HD"},
        {"Make": "DJI", "Model": "Matrice 300 RTK H20T"},
        {"Make": "Bosch", "Model": "FLEXIDOME IP 5000i"},
    ]

    SOFTWARE_TOOLS = [
        "Adobe Photoshop 24.1.0",
        "Lavf/58.76.100",
        "Adobe Premiere Pro 23.0.0",
        "PyMuPDF 1.22.5",
        "ElevenLabs Neural Voice Synthesizer v2.1",
        "Cobalt Strike Beacon v4.8",
        "FFmpeg 6.0-static",
        "DocuSign Signature Engine v3.4",
        "Wav2Lip Neural Blending Pipeline",
        "Autodesk AutoCAD 2024.1",
    ]

    AUTHORS = [
        "Elena Rostova",
        "A. V. Romanov",
        "Marcus Vance",
        "Dr. K. S. Nair",
        "Victor Sterling",
        "David Chen",
        "Captain H. Lindqvist",
        "N. A. Petrov",
    ]

    # Shared exact hashes to create cross-case malware/document intelligence
    SHARED_HASH_CLUSTERS = [
        ("malware_lockbit3_dropper", "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"),
        ("forged_swift_routing_slip", "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"),
        ("deepfake_source_vocoder_bank", "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a"),
        ("unauthorized_fpga_patch_bitstream", "ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d"),
    ]

    # Track evidence by domain
    video_items = [e for e in evidence_items if e.media_type == "video"]
    image_items = [e for e in evidence_items if e.media_type == "image"]
    doc_items = [e for e in evidence_items if e.media_type == "document"]
    audio_items = [e for e in evidence_items if e.media_type == "audio"]

    print(f"Media Breakdown: {len(video_items)} videos, {len(image_items)} images, {len(doc_items)} docs, {len(audio_items)} audio")

    # 1. Assign Cameras to Videos and Images
    for idx, ev in enumerate(video_items + image_items):
        details = ev.get_details()
        exif = details.get("exif") or {}
        # Every 4th item shares a camera with another case
        cam = CAMERAS[idx % len(CAMERAS)]
        exif["Make"] = cam["Make"]
        exif["Model"] = cam["Model"]
        details["exif"] = exif
        ev.details = json.dumps(details)

    # 2. Assign Software to manipulated & reviewed items
    manipulated_items = [e for e in evidence_items if e.score is not None and e.score < 75]
    for idx, ev in enumerate(manipulated_items):
        details = ev.get_details()
        exif = details.get("exif") or {}
        props = details.get("properties") or {}
        tags = details.get("tags") or {}

        sw = SOFTWARE_TOOLS[idx % len(SOFTWARE_TOOLS)]
        exif["Software"] = sw
        props["Producer"] = sw
        props["Application"] = sw
        tags["encoder"] = sw
        details["exif"] = exif
        details["properties"] = props
        details["tags"] = tags
        ev.details = json.dumps(details)

    # 3. Assign Document Authors to docs
    for idx, ev in enumerate(doc_items):
        details = ev.get_details()
        props = details.get("properties") or {}
        auth = AUTHORS[idx % len(AUTHORS)]
        props["Author"] = auth
        props["creator"] = auth
        props["last_modified_by"] = auth
        details["properties"] = props
        ev.details = json.dumps(details)

    # 4. Inject 4 pairs of identical SHA-256 hashes across different cases
    for c_name, sha in SHARED_HASH_CLUSTERS:
        # Pick 2 evidence items from different cases
        c_items = [e for e in evidence_items if e.case_id > 1 and e.media_type == "document"]
        if len(c_items) >= 2:
            idx1 = random.randint(0, len(c_items) - 1)
            idx2 = (idx1 + 7) % len(c_items)
            c_items[idx1].sha256 = sha
            c_items[idx2].sha256 = sha

    # 5. Inject pHash visual near-duplicates for deepfake/video evidence
    phash_seeds = [
        "a1b2c3d4e5f60718",
        "ffff0000aaaa5555",
        "1234567890abcdef",
        "8888777766665555",
    ]
    for ph in phash_seeds:
        eligible = [e for e in video_items + image_items if e.case_id > 2]
        if len(eligible) >= 2:
            e1 = random.choice(eligible)
            eligible.remove(e1)
            e2 = random.choice(eligible)
            e1.phash = ph
            # small 2-bit variation
            e2.phash = ph[:-1] + ("9" if ph[-1] != "9" else "8")

    db.commit()
    print("Metadata enrichment successfully committed to database!")

    # Verify cross-case graph
    from app.models import User
    u = db.query(User).first()
    g = get_cross_case_graph(db, u)
    print(f"Graph Results after enrichment:")
    print(f"Total Nodes: {len(g['nodes'])}")
    print(f"Total Cross-Case Edges: {len(g['edges'])}")
    
    edge_types = {}
    for e in g['edges']:
        t = e['type']
        edge_types[t] = edge_types.get(t, 0) + 1
    print(f"Edge Breakdown: {edge_types}")
    db.close()

if __name__ == "__main__":
    enrich_evidence_metadata()
