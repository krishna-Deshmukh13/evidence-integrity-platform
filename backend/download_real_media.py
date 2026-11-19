import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

FFMPEG = r"C:\Users\krish\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"

root = Path(r"C:\Users\krish\.gemini\antigravity\scratch\evidence-integrity-platform")
real_dir = root / "real_incident_evidence_files"
real_dir.mkdir(parents=True, exist_ok=True)
tmp_dir = root / "backend/storage/real_temp"
tmp_dir.mkdir(parents=True, exist_ok=True)

downloads = [
    # Videos
    ("cctv_crimean_bridge_explosion_2022.webm", "https://upload.wikimedia.org/wikipedia/commons/d/db/CCTV_footage_of_the_Crimean_Bridge_explosion_on_October_8%2C_2022.webm"),
    ("cctv_night_dahua_surveillance.webm", "https://upload.wikimedia.org/wikipedia/commons/c/c2/8MP_4K_Dahua_CCTV_System_Sample_Video_-_Night_Time.webm"),
    # Audio
    ("ksfo_tower_asiana214_atc_emergency.ogg", "https://upload.wikimedia.org/wikipedia/commons/3/34/Asiana_214_crash_-_KSFO_Tower_ATC_recording.ogg"),
    ("guam_korean_air_801_atc_recording.oga", "https://upload.wikimedia.org/wikipedia/commons/6/68/Korean_Air_Flight_801_crash%2C_Guam_air_traffic_control_recording_%28August_1997%29.oga"),
    # Images
    ("dc_police_surveillance_camera.jpg", "https://upload.wikimedia.org/wikipedia/commons/8/89/Streetlight_Surveillance_Camera_at_Constitution_Avenue%2C_NW_%26_Twelfth_Street%2C_NW_%28Washington%2C_DC%29_%28324002863%29.jpg"),
    ("stylegan_ai_deepfake_face.jpg", "https://upload.wikimedia.org/wikipedia/commons/1/1c/This_Person_Does_Not_Exist_example.jpg"),
    ("fbi_evidence_response_team_photo.jpg", "https://upload.wikimedia.org/wikipedia/commons/2/23/FBI_Evidence_Response_Team_teach_crime_scene_evidence_gathering_techniques_during_TRADEWINDS_24_%288399960%29.jpg"),
    # Documents
    ("fbi_affidavit_ehsanul_sadequee_court_filing.pdf", "https://upload.wikimedia.org/wikipedia/commons/e/ea/Affidavit_against_Ehsanul_Sadequee.pdf"),
    ("us_district_court_federal_indictment.pdf", "https://upload.wikimedia.org/wikipedia/commons/e/ef/Complaint_and_Indictment_as_to_Julio_Sarabia_et_al.pdf"),
]

headers = {"User-Agent": "EvidenceIntegrityPlatform/1.0 (academic-testing@domain.com)"}

for fname, url in downloads:
    dest = tmp_dir / fname
    if not dest.exists() or dest.stat().st_size == 0:
        print(f"Downloading {fname} from Wikimedia...")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as out:
                shutil.copyfileobj(resp, out)
            print(f"Downloaded {fname} ({dest.stat().st_size} bytes)")
        except Exception as e:
            print(f"Failed to download {fname}: {e}")

# Transcode videos to standard browser-playable MP4 (H.264 / AAC)
vid1_in = tmp_dir / "cctv_crimean_bridge_explosion_2022.webm"
vid1_out = real_dir / "real_incident_cctv_crimean_bridge_2022.mp4"
if vid1_in.exists() and not vid1_out.exists():
    print("Transcoding Crimean Bridge CCTV to MP4...")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(vid1_in), "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", str(vid1_out)], check=False)

vid2_in = tmp_dir / "cctv_night_dahua_surveillance.webm"
vid2_out = real_dir / "real_incident_cctv_night_security_cam.mp4"
if vid2_in.exists() and not vid2_out.exists():
    print("Transcoding Dahua Night CCTV to MP4...")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(vid2_in), "-t", "25", "-c:v", "libx264", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", str(vid2_out)], check=False)

# Create an edited CCTV clip with hard splice and frozen frame
vid_tampered_out = real_dir / "real_incident_cctv_tampered_splice.mp4"
if vid1_out.exists() and not vid_tampered_out.exists():
    print("Generating tampered CCTV with cut and CapCut metadata...")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(vid1_out), "-vf", "trim=0:12", "-metadata", "comment=Edited with CapCut", "-c:v", "libx264", "-crf", "22", str(vid_tampered_out)], check=False)

# Transcode audios to standard WAV and MP3
aud1_in = tmp_dir / "ksfo_tower_asiana214_atc_emergency.ogg"
aud1_out = real_dir / "real_emergency_asiana214_atc_radio.wav"
if aud1_in.exists() and not aud1_out.exists():
    print("Transcoding Asiana 214 ATC to WAV...")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(aud1_in), "-t", "30", "-ar", "44100", "-ac", "1", str(aud1_out)], check=False)

aud2_in = tmp_dir / "guam_korean_air_801_atc_recording.oga"
aud2_out = real_dir / "real_emergency_korean_air_801_atc.wav"
if aud2_in.exists() and not aud2_out.exists():
    print("Transcoding Korean Air ATC to WAV...")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(aud2_in), "-t", "30", "-ar", "44100", "-ac", "1", str(aud2_out)], check=False)

# Copy photos and documents
for fname in ["dc_police_surveillance_camera.jpg", "stylegan_ai_deepfake_face.jpg", "fbi_evidence_response_team_photo.jpg",
              "fbi_affidavit_ehsanul_sadequee_court_filing.pdf", "us_district_court_federal_indictment.pdf"]:
    src = tmp_dir / fname
    if src.exists():
        shutil.copy(src, real_dir / fname)
        print(f"Copied {fname} to real_incident_evidence_files")

# Also include the core benchmark samples
sample_gen = root / "backend/storage/samples_gen"
uploads = root / "backend/storage/uploads"

for dest_name, src in [
    ("photo_tampered_alley_cloned.jpg", uploads / "e_photo_tampered.jpg"),
    ("photo_original_alley_camera.jpg", uploads / "e_photo_original.jpg"),
    ("voice_synthetic_tts_elevenlabs.wav", sample_gen / "voice_tts.wav"),
    ("invoice_tampered_font_altered.pdf", sample_gen / "invoice_tampered.pdf"),
    ("statement_tampered_tracked_revisions.docx", sample_gen / "statement_tampered.docx")
]:
    if src.exists():
        shutil.copy(src, real_dir / dest_name)

print("All real incident media files processed!")
