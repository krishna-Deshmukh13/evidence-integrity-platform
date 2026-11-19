AI DIGITAL EVIDENCE INTEGRITY & FORENSICS PLATFORM
===================================================
Sample Evidence Test Suite for Local Upload & Analysis

This directory contains authentic and manipulated multi-media files across
all four forensic domains (Image, Audio, Video, Document). You can upload
these files individually or as a whole folder using the 'Add evidence' button.

1. IMAGES (.jpg)
----------------
- photo_tampered.jpg:
  Manipulated scene with cloned brick wall patch (196 keypoint matches),
  pasted jacket in right doorway, and Adobe Photoshop EXIF metadata.
  Expected: Score ~42 (Likely manipulated). Triggers: Clone map, ELA, Noise.

- photo_original.jpg:
  Authentic camera photo with continuous noise and valid original EXIF.
  Expected: Score 100 (Consistent).

- photo_stripped.jpg:
  Original photo with camera metadata removed.
  Expected: Score 94 (Consistent). Triggers: Low-severity metadata flag.

- ai_generated_pig.jpg:
  Machine-generated synthetic image.
  Expected: Score ~42 (Likely manipulated). Triggers: SwinV2 AI image detector.

- cctv_suspect_face_crop.jpg:
  Deepfake face alteration in surveillance footage.
  Expected: Score ~48 (Likely manipulated). Triggers: ViT Face deepfake detector.

2. AUDIO (.wav)
---------------
- voice_tts.wav:
  Synthesized text-to-speech audio with two digital silence splices (0 amp)
  and 7.0 kHz bandwidth cutoff.
  Expected: Score ~45 (Likely manipulated). Triggers: wav2vec2 synthetic voice,
  digital silence detector, frequency bandwidth check.

- voice_human.wav:
  Natural human acoustic voice baseline with smooth room reverb.
  Expected: Score 100 (Consistent).

- ceo_extortion_voicemail.wav:
  Cloned voice recording with acoustic synthesis artefacts.
  Expected: Score ~44 (Likely manipulated). Triggers: Voice cloning detector.

3. VIDEO (.mp4)
---------------
- video_edited.mp4:
  Edited surveillance footage featuring hard cuts at 9.7 seconds, a frozen
  frame interval (7.2s - 9.7s), and CapCut container metadata tag.
  Expected: Score ~54 (Needs review). Triggers: Hard cut, frozen frames.

- video_original.mp4:
  Continuous, unedited CCTV recording baseline without splices.
  Expected: Score ~82 (Consistent).

- security_checkpoint_gate4.mp4:
  Perimeter camera recording baseline.
  Expected: Score ~90 (Consistent).

4. DOCUMENTS (.pdf, .docx)
--------------------------
- invoice_tampered.pdf:
  Manipulated invoice with substituted font (Times-Roman over Helvetica on
  amounts), white-out concealment rectangle, and 2 incremental PDF saves.
  Expected: Score ~27 (Likely manipulated). Triggers: Font forensics, whiteout.

- invoice_original.pdf:
  Single-save authentic PDF invoice with matching typography.
  Expected: Score 100 (Consistent).

- wire_transfer_receipt.pdf:
  Receipt with post-signing byte modifications invalidating digital signature.
  Expected: Score ~35 (Likely manipulated).

- statement_tampered.docx:
  Witness statement with tracked revisions altering key deposition testimony
  ('did not see' -> 'clearly saw').
  Expected: Score ~74 (Needs review). Triggers: Tracked changes.

- statement_original.docx:
  Clean deposition witness statement baseline.
  Expected: Score 100 (Consistent).
