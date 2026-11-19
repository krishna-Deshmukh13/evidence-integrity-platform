"""Generate and insert 100 realistic forensic crime, cyber-incident, and financial investigation cases."""
import os
import sys
import json
import random
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.environ.setdefault("EI_STORAGE_DIR", str(backend_dir / "storage"))

from app import config
from app.database import SessionLocal, init_db
from app.models import Case, CaseMember, Evidence, Finding, CustodyEvent, User, now_iso

CASE_TEMPLATES = [
    # 1-10: Cyber Warfare & Critical Infrastructure
    ("CY-2024-1011", "National Power Grid SCADA Telemetry Override & Substation Blackout", "Insp. Meera Kulkarni", [
        ("scada_modbus_pmu_stream_sub44.pcap", "document", 18, "Likely manipulated", "Packet injection detected in Modbus TCP frame headers"),
        ("substation_control_log_audit.csv", "document", 68, "Needs review", "Discontinuous timestamps between 02:14:00 and 02:18:30 UTC"),
    ]),
    ("CY-2024-1014", "Municipal Water Treatment Chemical Dosing PLC Firmware Tampering", "SI Rohan Patil", [
        ("plc_allen_bradley_firmware_dump.bin", "document", 12, "Likely manipulated", "Unauthorized hardcoded override routine found in ladder logic"),
        ("hmi_alarm_snapshot_screen.png", "image", 88, "Consistent", "Authentic HMI error state screenshot"),
    ]),
    ("CY-2024-1019", "Nuclear Research Reactor Secondary Coolant Loop Sensor Spoofing", "Insp. Meera Kulkarni", [
        ("reactor_coolant_telemetry_dump.csv", "document", 24, "Likely manipulated", "Synthesized thermal oscillation curve inconsistent with pump RPM"),
        ("control_room_dashcam_feed.mp4", "video", 91, "Consistent", "Physical control room CCTV verifies operator response"),
    ]),
    ("CY-2024-1025", "High-Speed Rail Interlocking Signal Tampering & Track Circuit Bypass", "Krishna Deshmukh", [
        ("interlocking_relay_controller_memory.hex", "document", 15, "Likely manipulated", "Injected memory patch forcing false clear aspect on signal 402B"),
        ("cab_radio_audio_recording.wav", "audio", 82, "Consistent", "Cab dispatch radio voice track authenticated with VHF carrier frequency"),
    ]),
    ("CY-2024-1033", "Metro Airport Radar Beacon ADS-B Ghost Aircraft Injection", "Insp. Meera Kulkarni", [
        ("sdr_raw_rf_capture_1090mhz.bin", "document", 31, "Likely manipulated", "RF carrier phase anomalies indicating software-defined radio spoofing"),
        ("tower_radar_track_snapshot.png", "image", 72, "Needs review", "Target track displays impossible acceleration vector (Mach 4.2)"),
    ]),
    ("CY-2024-1042", "Port Container Terminal Automated Crane Fleet Ransomware Lockdown", "SI Rohan Patil", [
        ("crane_telematics_broker_log.json", "document", 22, "Likely manipulated", "Wiper routine overwrote container coordinate offsets"),
        ("terminal_gate_surveillance_cam08.mp4", "video", 94, "Consistent", "Uncut surveillance footage showing crane boom deadlock"),
    ]),
    ("CY-2024-1051", "Subsea Telecommunications Fiber Optic Repeater Signal Splice", "Insp. Meera Kulkarni", [
        ("otdr_optical_time_domain_reflectometry.pdf", "document", 29, "Likely manipulated", "Unaccounted 1.4 dB attenuation step at km marker 142.8"),
        ("repeater_housing_inspection_photo.jpg", "image", 86, "Consistent", "Deep-sea ROV imagery shows mechanical clamp abrasions"),
    ]),
    ("CY-2024-1060", "Hospital Intensive Care Central Telemetry Gateway Compromise", "Nida Shaikh", [
        ("infusion_pump_ethernet_trace.pcap", "document", 16, "Likely manipulated", "Malicious broadcast packet re-calibrating flow rate limits"),
        ("cardiac_monitor_telemetry_export.csv", "document", 64, "Needs review", "Missing cryptographic signature from bedside telemetry base"),
    ]),
    ("CY-2024-1068", "Commercial Gas Pipeline Supervisory Valve Pressure Sensor Spoof", "Kavya Rao", [
        ("pressure_transducer_telemetry_stream.csv", "document", 25, "Likely manipulated", "Artificially suppressed delta-P readings during compressor surge"),
        ("pump_station_exterior_cctv.mp4", "video", 89, "Consistent", "Exterior PTZ video shows emergency blow-off valve actuation"),
    ]),
    ("CY-2024-1077", "Space Agency Ground Satellite Uplink Command Injection Attack", "Insp. Meera Kulkarni", [
        ("ground_station_modem_demod_capture.bin", "document", 14, "Likely manipulated", "Unauthorized command frames injected using stolen cryptographic ephemerals"),
        ("parabolic_dish_pointing_telemetry.csv", "document", 95, "Consistent", "Antenna tracking telemetry authenticated"),
    ]),

    # 11-20: Financial Crimes, Wire Fraud & Crypto Laundering
    ("FIN-2024-2011", "Central Reserve Bank SWIFT MT103 Wire Authorization Forgery", "Insp. Meera Kulkarni", [
        ("swift_mt103_wire_confirmation_92m.pdf", "document", 10, "Likely manipulated", "Modified SWIFT tag :72: and mismatched BIC cryptographic checksum"),
        ("treasury_officer_digital_cert_chain.pem", "document", 28, "Likely manipulated", "Revoked intermediary CA certificate used for digital sign-off"),
    ]),
    ("FIN-2024-2018", "Offshore Hedge Fund Collateralized Debt Obligation Ledger Fraud", "SI Rohan Patil", [
        ("nav_valuation_spreadsheet_q3_final.xlsx", "document", 35, "Likely manipulated", "Hidden macro overriding mark-to-market valuations with fixed multipliers"),
        ("auditor_confirmation_letter_signed.pdf", "document", 19, "Likely manipulated", "Forged audit partner signature and cloned firm letterhead"),
    ]),
    ("FIN-2024-2026", "Tornado Cash Crypto Tumbler Layering & Sanctions Evasion", "Krishna Deshmukh", [
        ("ethereum_mixer_deposit_relay_graph.json", "document", 89, "Consistent", "Valid on-chain transaction graph with zero-knowledge proof verification"),
        ("escrow_smart_contract_decompiled.sol", "document", 42, "Needs review", "Proxy contract storage slot collision vulnerability detected"),
    ]),
    ("FIN-2024-2035", "Billion-Dollar Sovereign Wealth Fund Shell Corporation Wire", "Insp. Meera Kulkarni", [
        ("commercial_bank_wire_routing_slip.pdf", "document", 18, "Likely manipulated", "Altered recipient IBAN account routing number"),
        ("deputy_governor_authorisation_memo.pdf", "document", 27, "Likely manipulated", "Cloned executive letterhead and cut-and-paste signature"),
    ]),
    ("FIN-2024-2044", "High-Frequency Trading Microsecond Timestamp Arbitrage Tampering", "SI Rohan Patil", [
        ("nasdaq_itch_market_feed_capture.pcap", "document", 34, "Likely manipulated", "PTP hardware timestamp offset altered by 42 microseconds"),
        ("fpga_gateway_execution_audit.log", "document", 84, "Consistent", "FPGA kernel log confirms timestamp clock synchronization loss"),
    ]),
    ("FIN-2024-2053", "Commercial Real Estate Mezzanine Loan Fraud & Title Deed Duplication", "Kavya Rao", [
        ("metropolitan_land_registry_deed_folio49.pdf", "document", 22, "Likely manipulated", "Cloned watermarks and fraudulent registrar seal layer"),
        ("property_surveyor_topographic_photo.jpg", "image", 91, "Consistent", "Exif GPS correlates with surveyed municipal boundaries"),
    ]),
    ("FIN-2024-2062", "Commodity Trading Synthetic Warehouse Receipt Double-Pledging", "Krishna Deshmukh", [
        ("bonded_warehouse_copper_cathode_receipt.pdf", "document", 15, "Likely manipulated", "Serial numbers duplicate an existing pledged lot in Rotterdam"),
        ("warehouse_manager_notarized_affidavit.pdf", "document", 74, "Needs review", "Notary seal impression matches standard die but lacks entry registration"),
    ]),
    ("FIN-2024-2071", "Cross-Border Trade Invoice Over-Billing & Capital Flight Mechanism", "Nida Shaikh", [
        ("shipping_manifest_electronics_freight.pdf", "document", 39, "Likely manipulated", "Valuation overstated by 650% relative to physical customs weight"),
        ("customs_xray_cargo_inspection_scan.png", "image", 92, "Consistent", "X-ray density analysis reveals low-grade scrap rather than server CPUs"),
    ]),
    ("FIN-2024-2080", "Venture Capital Seed Round Escrow Wallet Drain & Phishing Intercept", "SI Rohan Patil", [
        ("metamask_approval_transaction_raw.hex", "document", 20, "Likely manipulated", "Permit2 unlimited approval signature phished via counterfeit dApp"),
        ("discord_investor_chat_export.json", "document", 87, "Consistent", "Chat timestamps corroborate credential phishing campaign timeline"),
    ]),
    ("FIN-2024-2089", "Central Securities Depository Bearer Bond Ledger Invalidation", "Insp. Meera Kulkarni", [
        ("custodial_participant_reconciliation_diff.csv", "document", 17, "Likely manipulated", "Unbalanced debit adjustment of $45M without counterparty ticket"),
        ("swift_mt542_free_delivery_instruction.txt", "document", 33, "Likely manipulated", "Counterparty BIC code invalid on stated settlement date"),
    ]),

    # 21-30: Deepfake Audio, Video & Biometric Fraud
    ("AV-2024-3012", "Multinational CEO Deepfake Audio Wire Transfer Authorization", "Insp. Meera Kulkarni", [
        ("ceo_phone_order_wire_authorization.wav", "audio", 8, "Likely manipulated", "Neural vocoder artifacts, absence of nasal resonance and synthetic pitch contour"),
        ("telephony_pbx_sip_signaling_trace.pcap", "document", 26, "Likely manipulated", "SIP caller ID spoofed via offshore VoIP termination provider"),
    ]),
    ("AV-2024-3021", "State Governor Defamatory Deepfake Press Conference Broadcast", "SI Rohan Patil", [
        ("governor_emergency_declaration_broadcast.mp4", "video", 14, "Likely manipulated", "Lip-sync GAN boundary warping and unnatural micro-saccadic eye movement"),
        ("studio_broadcast_master_audio_feed.wav", "audio", 21, "Likely manipulated", "Spectral phase discontinuities characteristic of ElevenLabs voice cloning"),
    ]),
    ("AV-2024-3030", "Court Exhibit Deepfake Witness Deposition Video Tampering", "Krishna Deshmukh", [
        ("witness_sworn_videotaped_deposition.mp4", "video", 11, "Likely manipulated", "Face-swap seam visible along jawline during head rotation at 14:22"),
        ("deposition_stenographer_audio_recording.wav", "audio", 93, "Consistent", "Continuous room acoustic tone matches analog microphone characteristics"),
    ]),
    ("AV-2024-3039", "Biometric Facial Recognition E-Passport Gate Spoofing Attack", "Kavya Rao", [
        ("border_control_kiosk_camera_still.jpg", "image", 23, "Likely manipulated", "High-resolution 3D latex prosthetic texture detected on infrared sensor"),
        ("icao_doc9303_epassport_chip_dump.bin", "document", 88, "Consistent", "Cryptographic active authentication passed using stolen valid credentials"),
    ]),
    ("AV-2024-3048", "Celebrity Deepfake Endorsement Crypto Scam Promotion", "Nida Shaikh", [
        ("viral_social_media_video_ad.mp4", "video", 16, "Likely manipulated", "Wav2Lip model blending seams detected around mouth aperture"),
        ("advertiser_account_payment_receipt.pdf", "document", 90, "Consistent", "Ad billing record authenticated from major ad platform CDN"),
    ]),
    ("AV-2024-3057", "Emergency 911 Hostage Situation Synthetic Voice Swatting Call", "SI Rohan Patil", [
        ("911_dispatch_emergency_call_audio.wav", "audio", 19, "Likely manipulated", "Text-to-speech phonetic transitions and zero ambient background acoustics"),
        ("cellular_tower_cdr_call_detail_record.csv", "document", 38, "Needs review", "VoIP trunk routing through non-geographical IP gateway"),
    ]),
    ("AV-2024-3066", "High-Security Vault Voiceprint Biometric Intercept & Playback", "Insp. Meera Kulkarni", [
        ("vault_intercom_access_phrase_audio.wav", "audio", 12, "Likely manipulated", "Replay attack: frequency response peaks from secondary speaker cone"),
        ("security_console_access_audit.log", "document", 96, "Consistent", "Badge access event logged concurrently at outer perimeter gate"),
    ]),
    ("AV-2024-3075", "Diplomatic Summit Audio Leak Fabrication & Geo-Political Disinformation", "Krishna Deshmukh", [
        ("closed_door_bilateral_talks_audio.mp3", "audio", 9, "Likely manipulated", "Deepfake speech synthesized with diffusion model, temporal jitter detected"),
        ("embassy_acoustic_room_impulse_response.wav", "audio", 32, "Likely manipulated", "Reverberation profile does not match physical room geometry"),
    ]),
    ("AV-2024-3084", "Corporate Hostile Takeover False Whistleblower Video Manifest", "SI Rohan Patil", [
        ("whistleblower_video_confession.mp4", "video", 27, "Likely manipulated", "Synthetic blur applied to conceal face swap boundary artifacts"),
        ("encrypted_usb_drive_metadata_dump.txt", "document", 85, "Consistent", "NTFS volume serial number and creation timestamp authenticated"),
    ]),
    ("AV-2024-3093", "Automated Banking Remote KYC Video Selfie Liveness Bypass", "Kavya Rao", [
        ("kyc_liveness_check_video_recording.mp4", "video", 15, "Likely manipulated", "Pre-recorded digital playback displayed on high-res iPad screen"),
        ("mobile_banking_app_device_fingerprint.json", "document", 22, "Likely manipulated", "Rooted device using virtual camera injection hook"),
    ]),

    # 31-40: CCTV, Physical Surveillance & Collision Forensics
    ("CCTV-2024-4010", "Metropolitan Expressway Fatal Collision Hit-and-Run Investigation", "Insp. Meera Kulkarni", [
        ("expressway_toll_plaza_camera_ch02.mp4", "video", 95, "Consistent", "Uncut H.264 stream with verified GOP structure and timecode sync"),
        ("suspect_vehicle_side_impact_photo.jpg", "image", 92, "Consistent", "Paint transfer marks match victim vehicle factory clearcoat"),
    ]),
    ("CCTV-2024-4019", "Jewelry District Diamond Vault Heist Footage Time-Splice", "SI Rohan Patil", [
        ("vault_corridor_dome_camera_04.mp4", "video", 7, "Likely manipulated", "7-minute static frame loop spliced into stream to conceal entry"),
        ("motion_sensor_hardware_event_log.csv", "document", 89, "Consistent", "PIR sensor registered activity during spliced video window"),
    ]),
    ("CCTV-2024-4028", "Casino Cash Cage Robbery Surveillance Timestamp Tampering", "Krishna Deshmukh", [
        ("cash_cage_ptz_overhead_camera.mp4", "video", 18, "Likely manipulated", "Timestamp OSD re-rendered in post-production with mismatched font kerning"),
        ("slot_floor_wide_angle_camera.mp4", "video", 94, "Consistent", "Synchronous baseline footage confirms 8-minute temporal discrepancy"),
    ]),
    ("CCTV-2024-4037", "Armored Transit Cash-in-Transit Vehicle Ambush & Robbery", "Insp. Meera Kulkarni", [
        ("armored_truck_forward_dashcam.mp4", "video", 96, "Consistent", "Multi-camera vehicle DVR footage verified with hardware GPS lock"),
        ("depot_loading_bay_perimeter_cctv.mp4", "video", 91, "Consistent", "High-angle perimeter camera confirms suspect vehicle trailing route"),
    ]),
    ("CCTV-2024-4046", "Industrial Warehouse Arson Fire Sequence & Frame Decimation", "SI Rohan Patil", [
        ("loading_dock_fire_origin_cctv.mp4", "video", 21, "Likely manipulated", "Keyframes deleted between 03:12:45 and 03:14:10 to conceal accelerant pour"),
        ("thermal_imaging_sensor_csv_log.csv", "document", 83, "Consistent", "Thermal sensor registers rapid 400C thermal spike matching arson profile"),
    ]),
    ("CCTV-2024-4055", "Diplomatic Compound Gate Ramming & Security Breach", "Insp. Meera Kulkarni", [
        ("main_security_gate_camera_angle_a.mp4", "video", 97, "Consistent", "Full-frame 60fps security recording authenticated with digital watermark"),
        ("ballistic_glass_shatter_inspection.jpg", "image", 93, "Consistent", "Impact fracture patterns consistent with vehicle kinetic force"),
    ]),
    ("CCTV-2024-4064", "ATM Vestibule Pin-Pad Skimmer & Micro-Cam Placement", "Nida Shaikh", [
        ("atm_lobby_ceiling_fisheye_cam.mp4", "video", 88, "Consistent", "Footage captures suspect installing counterfeit fascia and pin-hole camera"),
        ("skimmer_extracted_flash_memory_dump.bin", "document", 94, "Consistent", "Magnetic stripe track-2 dumps recovered from flash EEPROM"),
    ]),
    ("CCTV-2024-4073", "Superyacht Marina Berthing Dock Hit-and-Run Damage", "Kavya Rao", [
        ("harbor_master_panoramic_camera.mp4", "video", 90, "Consistent", "Clear wide-angle coverage tracking hull collision event"),
        ("damaged_composite_hull_ultrasound_scan.pdf", "document", 92, "Consistent", "Delamination depth ultrasound scan verified"),
    ]),
    ("CCTV-2024-4082", "Freight Train Derailment Hazardous Material Tanker Spill", "SI Rohan Patil", [
        ("trackside_hot_box_detector_camera.mp4", "video", 93, "Consistent", "Wheel bearing thermal overload visible 3 miles prior to derailment"),
        ("locomotive_event_recorder_blackbox.csv", "document", 97, "Consistent", "Dynamic braking and throttle telemetry matches rail profile"),
    ]),
    ("CCTV-2024-4091", "High-Security Prison Yard Contraband Drone Delivery", "Krishna Deshmukh", [
        ("prison_north_perimeter_optical_cam.mp4", "video", 87, "Consistent", "Thermal and visual dual-stream video captures drone drop sequence"),
        ("recovered_quadcopter_flight_telemetry.log", "document", 91, "Consistent", "Extracted flight logs match GPS track recorded on CCTV"),
    ]),

    # 41-50: Document Forgery, Notary Fraud & Legal Exhibits
    ("DOC-2024-5011", "Billionaire Estate Holographic Will Signature & Page Substitution", "Insp. Meera Kulkarni", [
        ("last_will_and_testament_signed_2021.pdf", "document", 13, "Likely manipulated", "Page 4 font metrics, kerning, and paper fiber weave mismatch pages 1-3"),
        ("probate_lawyer_desk_copy_scan.pdf", "document", 89, "Consistent", "Law office microfiche archive copy confirms original legacy bequest"),
    ]),
    ("DOC-2024-5020", "State Supreme Court Settlement Agreement Alteration", "SI Rohan Patil", [
        ("binding_arbitration_award_executed.pdf", "document", 17, "Likely manipulated", "Digital signature block copied from unrelated contract; digest mismatch"),
        ("arbitrator_email_transmission_eml.txt", "document", 92, "Consistent", "DKIM and SPF headers authenticate original settlement dispatch"),
    ]),
    ("DOC-2024-5029", "Commercial Bank Mortgage Discharge Notary Stamp Cloned Die", "Kavya Rao", [
        ("mortgage_release_satisfaction_deed.pdf", "document", 22, "Likely manipulated", "Pixel-perfect clone of notary stamp with duplicated ink splatter void"),
        ("state_notary_commission_record_check.pdf", "document", 96, "Consistent", "Official state registry confirms notary was deceased on document date"),
    ]),
    ("DOC-2024-5038", "Sovereign Bond Bearer Certificate Counterfeit Security Thread", "Insp. Meera Kulkarni", [
        ("treasury_bearer_bond_high_res_scan.tif", "image", 19, "Likely manipulated", "Intaglio printing rasterized via CMYK inkjet printer; microtext blurred"),
        ("uv_fluorescence_spectral_analysis.jpg", "image", 14, "Likely manipulated", "Missing red/green dual phosphor fluorescence under 365nm UV excitation"),
    ]),
    ("DOC-2024-5047", "Corporate Share Purchase Agreement Annexure Tampering", "Krishna Deshmukh", [
        ("share_purchase_agreement_final_v4.pdf", "document", 26, "Likely manipulated", "Schedule 3 EBITDA earnout milestones replaced post-signing"),
        ("docu_sign_envelope_audit_trail.pdf", "document", 39, "Needs review", "Audit trail exhibits hash mismatch with final embedded PDF object"),
    ]),
    ("DOC-2024-5056", "Customs Clean Report of Findings Inspection Certificate Forgery", "Nida Shaikh", [
        ("bureau_veritas_inspection_certificate.pdf", "document", 21, "Likely manipulated", "Forged inspector stamp and invalid certification tracking code"),
        ("origin_port_customs_declaration.pdf", "document", 88, "Consistent", "Authentic departure manifest confirms container contents mismatch"),
    ]),
    ("DOC-2024-5065", "Clinical Trial Patient Informed Consent Form Retroactive Signature", "Insp. Meera Kulkarni", [
        ("patient_consent_form_study_onc_04.pdf", "document", 18, "Likely manipulated", "Ballpoint ink chromatographic aging analysis indicates post-dated execution"),
        ("hospital_irb_approval_registry.csv", "document", 90, "Consistent", "Institutional Review Board log indicates patient enrolled prior to consent date"),
    ]),
    ("DOC-2024-5074", "Commercial Patent Assignment Deed Intellectual Property Theft", "SI Rohan Patil", [
        ("patent_office_assignment_record_form.pdf", "document", 24, "Likely manipulated", "Assignor signature forged using vector spline stroke synthesis"),
        ("inventor_affidavit_sworn_deposition.pdf", "document", 94, "Consistent", "Original inventor sworn statement disclaiming signature transfer"),
    ]),
    ("DOC-2024-5083", "International Maritime Bill of Lading Cargo Diversion Fraud", "Kavya Rao", [
        ("ocean_bill_of_lading_maersk_line.pdf", "document", 16, "Likely manipulated", "Notify party altered from primary consignee to fictitious shell entity"),
        ("port_container_gate_in_interchange.pdf", "document", 87, "Consistent", "Port terminal EDI interchange message records legitimate consignee"),
    ]),
    ("DOC-2024-5092", "Government Tender Public Works Procurement Bid Price Tampering", "Krishna Deshmukh", [
        ("sealed_tender_financial_proposal_bidder_c.pdf", "document", 23, "Likely manipulated", "Bid price page replaced with modified schedule matching competitor price minus 1%"),
        ("tender_box_vault_security_log.csv", "document", 31, "Likely manipulated", "Audit log shows unauthorized keycard access at 23:45 night before opening"),
    ]),

    # 51-60: Ransomware & Cyber Extortion
    ("CY-2024-6011", "Multinational Defense Contractor LockBit 3.0 Decryptor Header Forgery", "Insp. Meera Kulkarni", [
        ("lockbit3_decryptor_master_binary.exe", "document", 29, "Likely manipulated", "Executable payload contains secondary backdoor infostealer routine"),
        ("threat_actor_negotiation_chat_transcript.txt", "document", 93, "Consistent", "TOX chat logs corroborate ransom demand and Bitcoin wallet address"),
    ]),
    ("CY-2024-6019", "Automotive Assembly Line BlackCat/ALPHV Ransomware Outage", "SI Rohan Patil", [
        ("domain_controller_event_security.evtx", "document", 88, "Consistent", "Event logs track PsExec lateral movement and service termination"),
        ("assembly_plc_firmware_backup.bin", "document", 92, "Consistent", "Firmware integrity verified; outage isolated to Windows IT management tier"),
    ]),
    ("CY-2024-6028", "Major Health System Akira Ransomware Patient Record Exfiltration", "Nida Shaikh", [
        ("mega_nz_cloud_exfiltration_pcap.pcap", "document", 86, "Consistent", "TLS traffic metrics match 450GB exfiltration transfer to mega.nz"),
        ("compromised_vpn_gateway_audit.log", "document", 91, "Consistent", "Compromised SonicWall credential utilized without MFA token"),
    ]),
    ("CY-2024-6037", "Commercial Bank SWIFT Gateway HermeticWiper Malware Strike", "Insp. Meera Kulkarni", [
        ("disk_partition_table_sector0_dump.raw", "document", 12, "Likely manipulated", "Master Boot Record overwritten with HermeticWiper fragmentation driver"),
        ("backup_nas_immutable_snapshot_manifest.xml", "document", 95, "Consistent", "WORM immutable backup storage prevented secondary target encryption"),
    ]),
    ("CY-2024-6046", "Semiconductor Manufacturer Ransomware Supply Chain Extortion", "Krishna Deshmukh", [
        ("leaked_chipset_verilog_hdl_archive.tar.gz", "document", 89, "Consistent", "Authentic RTL proprietary microprocessor schematic source verified"),
        ("darkweb_leak_site_tor_screencap.png", "image", 94, "Consistent", "Tor onion leak portal screen capture authenticated with PGP signature"),
    ]),
    ("CY-2024-6055", "Regional Airline Dispatch System Phobos Ransomware Attack", "SI Rohan Patil", [
        ("flight_operations_sql_database_mdf.raw", "document", 33, "Needs review", "SQL page headers encrypted with AES-256; recovery script tested"),
        ("pilot_briefing_terminal_cctv.mp4", "video", 91, "Consistent", "Dispatcher video shows blue-screen cascading across terminal cluster"),
    ]),
    ("CY-2024-6064", "Global Logistics Freight Forwarder Royal Ransomware Intrusion", "Kavya Rao", [
        ("hyperv_vhd_virtual_disk_cluster.img", "document", 28, "Likely manipulated", "Virtual machine headers corrupted by Royal encryption routine"),
        ("firewall_fortigate_syslog_export.log", "document", 87, "Consistent", "Firewall logs identify Cobalt Strike C2 beaconing to Romanian IP"),
    ]),
    ("CY-2024-6073", "Petrochemical Refinery Distributed Control System DarkSide Variant", "Insp. Meera Kulkarni", [
        ("safety_instrumented_system_audit.evtx", "document", 92, "Consistent", "SIS air-gapped network successfully isolated; no safety trip compromise"),
        ("corporate_active_directory_ntds.dit", "document", 20, "Likely manipulated", "Active directory database extracted with secretsdump tool"),
    ]),
    ("CY-2024-6082", "University Research Nuclear Physics Lab Ransomware Attack", "Krishna Deshmukh", [
        ("high_performance_computing_slurm.log", "document", 85, "Consistent", "HPC job scheduler commandeered for Monero cryptomining before lock"),
        ("supercomputer_compute_node_snapshot.raw", "document", 78, "Needs review", "Cryptominer daemon disguised as mpi_worker process"),
    ]),
    ("CY-2024-6091", "Fintech Payment Processor Snatch Ransomware & POS Compromise", "SI Rohan Patil", [
        ("pos_terminal_tls_interception_dump.pcap", "document", 17, "Likely manipulated", "Memory scraper malware extracted track-1 unencrypted card data"),
        ("pci_dss_compliance_audit_report.pdf", "document", 90, "Consistent", "Previous QSA compliance certification documentation"),
    ]),

    # 61-70: Ballistics, Police Body-Cam & Crime Scene Evidence
    ("BAL-2024-7011", "Officer-Involved Shooting Incident Body-Worn Camera Audit", "Insp. Meera Kulkarni", [
        ("officer_patrol_bodycam_axon_body3.mp4", "video", 95, "Consistent", "Axon cryptographic container signature intact; audio pre-event buffer valid"),
        ("taser_7_deployment_event_telemetry.csv", "document", 94, "Consistent", "Taser trigger pull matches video audio synchronization within 0.12s"),
    ]),
    ("BAL-2024-7020", "Downtown Alleyway Homicide Body-Cam Selective Frame Redaction", "SI Rohan Patil", [
        ("patrolman_body_worn_camera_feed.mp4", "video", 14, "Likely manipulated", "42-second blackout edit spliced in; audio channel muted artificially"),
        ("patrol_cruiser_in_car_camera_mvr.mp4", "video", 92, "Consistent", "Patrol vehicle dashcam captured continuous reflection in storefront window"),
    ]),
    ("BAL-2024-7029", "Gang Task Force Warrant Raid Weapon Discharge Reconstruction", "Krishna Deshmukh", [
        ("tactical_officer_helmet_camera_01.mp4", "video", 91, "Consistent", "High-intensity tactical light footage authenticated with unbroken audio"),
        ("forensic_ballistics_striation_micrograph.jpg", "image", 96, "Consistent", "Comparative bullet striation matches recovered 9mm Glock 19 barrel"),
    ]),
    ("BAL-2024-7038", "Suburban Bank Robbery Armed Standoff Crime Scene Photogrammetry", "Kavya Rao", [
        ("crime_scene_laser_scanner_pointcloud.e57", "document", 97, "Consistent", "Leica BLK360 3D spatial scan verified with millimeter calibration targets"),
        ("bullet_trajectory_trajectory_rod_photo.jpg", "image", 93, "Consistent", "EXIF raw color space and camera focal distance validated"),
    ]),
    ("BAL-2024-7047", "Traffic Stop Narcotics Seizure Bodycam Missing Audio Buffer", "SI Rohan Patil", [
        ("deputy_sheriff_body_camera_axon.mp4", "video", 38, "Needs review", "30-second silent buffer lacks expected acoustic signature; sensor fault investigated"),
        ("dispatch_cad_event_chronology_log.pdf", "document", 90, "Consistent", "Computer Aided Dispatch timestamps align with traffic stop timeline"),
    ]),
    ("BAL-2024-7056", "Industrial Park Security Guard Shooting Trajectory Inconsistency", "Insp. Meera Kulkarni", [
        ("security_checkpoint_wall_ricochet_photo.jpg", "image", 19, "Likely manipulated", "EXIF modified; trajectory rod angle altered via Photoshop content-aware fill"),
        ("coroner_post_mortem_trajectory_report.pdf", "document", 94, "Consistent", "Forensic pathologist autopsy findings contradict edited photo angle"),
    ]),
    ("BAL-2024-7065", "Highway Patrol Pursuit High-Speed PIT Maneuver Collision", "Krishna Deshmukh", [
        ("patrol_vehicle_radar_and_video_stream.mp4", "video", 93, "Consistent", "Dual-lens dashcam and radar speed overlay verified with speedometer OBD-II"),
        ("airbag_control_module_crash_data_retrieval.pdf", "document", 96, "Consistent", "Bosch CDR event data recorder confirms brake application 0.8s prior"),
    ]),
    ("BAL-2024-7074", "High-Profile Diplomatic Motorcade Sniper Attack Ballistic Origin", "Insp. Meera Kulkarni", [
        ("motorcade_suv_armored_glass_impact_photo.jpg", "image", 97, "Consistent", "Radial spall patterns on Level B6 armor glass indicate 7.62x54mm round"),
        ("shotspotter_acoustic_sensor_triangulation.json", "document", 92, "Consistent", "Multi-sensor acoustic triangulation pinpoints muzzle flash to 6th floor rooftop"),
    ]),
    ("BAL-2024-7083", "Nightclub Exterior Mass Shooting Mobile Phone Video Verification", "Nida Shaikh", [
        ("bystander_iphone_crowd_video_4k.mov", "video", 89, "Consistent", "Apple QuickTime container metadata and camera lens distortion profiles match"),
        ("recovered_shell_casing_macro_photo.jpg", "image", 94, "Consistent", "Ejector mark impressions match Glock 17 recovered from trash bin"),
    ]),
    ("BAL-2024-7092", "Maritime Coast Guard Cutter Contraband Interdiction Warning Shots", "SI Rohan Patil", [
        ("cutter_bridge_flir_thermal_video.mp4", "video", 95, "Consistent", "FLIR SeaFLIR 280-HD gyro-stabilized thermal stream authenticated"),
        ("deck_log_navigational_entry_signed.pdf", "document", 91, "Consistent", "Official USCG deck log signed by Officer of the Deck"),
    ]),

    # 71-80: Pharmaceutical, Medical Devices & Clinical Trial Integrity
    ("MED-2024-8011", "Phase III Oncology Drug Clinical Trial Efficacy Data Falsification", "Insp. Meera Kulkarni", [
        ("clinical_trial_patient_cdisc_sdtm_data.csv", "document", 12, "Likely manipulated", "Tumor shrinkage measurements copied identically across 24 distinct patient IDs"),
        ("edc_electronic_data_capture_audit_trail.log", "document", 23, "Likely manipulated", "Bulk modification of RECIST 1.1 outcome fields from single admin IP"),
    ]),
    ("MED-2024-8020", "Cardiovascular Pacemaker Bluetooth Telemetry Buffer Overflow Exploit", "SI Rohan Patil", [
        ("pacemaker_rf_programmer_session_log.bin", "document", 16, "Likely manipulated", "Injected memory exploit code to force ventricular defibrillation shock"),
        ("patient_holter_ecg_telemetry_recording.edf", "document", 94, "Consistent", "Holter monitor ECG waveforms confirm sudden rhythm disturbance episode"),
    ]),
    ("MED-2024-8029", "Hospital Pharmacy Automated Narcotics Dispenser Inventory Skim", "Nida Shaikh", [
        ("pyxis_medstation_dispense_transaction_log.csv", "document", 22, "Likely manipulated", "Fictitious fentanyl waste entries logged under inactive nurse credential"),
        ("pharmacy_vault_pinhole_camera_still.jpg", "image", 91, "Consistent", "High-resolution camera captures unauthorized access to drawer 4"),
    ]),
    ("MED-2024-8038", "Surgical Robot Real-Time Tele-Operation Command Latency Injection", "Insp. Meera Kulkarni", [
        ("da_vinci_surgical_console_telemetry.pcap", "document", 18, "Likely manipulated", "Packet jitter injection introducing 480ms artificial control latency"),
        ("operating_theater_overhead_recorder.mp4", "video", 96, "Consistent", "Surgical camera footage shows mechanical arm oscillation during suture"),
    ]),
    ("MED-2024-8047", "Forensic Toxicology Laboratory Blood-Alcohol GC-MS Peak Manipulation", "Krishna Deshmukh", [
        ("gas_chromatography_mass_spec_chromatogram.cdf", "document", 15, "Likely manipulated", "Baseline noise artificially smoothed to erase ethanol peak at 2.4 min"),
        ("toxicology_lab_information_system_lims.log", "document", 29, "Likely manipulated", "Calibration curve slope manually overridden by laboratory technician"),
    ]),
    ("MED-2024-8056", "Gene Therapy Vector Potency Assay Spectrophotometry Forgery", "Kavya Rao", [
        ("elisa_plate_reader_raw_optical_density.xlsx", "document", 20, "Likely manipulated", "Optical density values generated using linear random number formula"),
        ("spectrophotometer_calibration_certificate.pdf", "document", 93, "Consistent", "Equipment calibration current; manipulation occurred in exported spreadsheet"),
    ]),
    ("MED-2024-8065", "Central Blood Bank Infectious Disease Screening ELISA Invalidation", "Insp. Meera Kulkarni", [
        ("hepatitis_c_antibody_screen_raw_run.txt", "document", 17, "Likely manipulated", "Cutoff threshold value altered to convert reactive specimens into negative"),
        ("donor_screening_questionnaire_scan.pdf", "document", 89, "Consistent", "Original paper intake forms indicate high-risk travel history disclosed"),
    ]),
    ("MED-2024-8074", "Commercial Diagnostic Laboratory Covid-19 RT-PCR Cycle Threshold Fraud", "SI Rohan Patil", [
        ("real_time_pcr_amplification_curves.csv", "document", 24, "Likely manipulated", "Amplification curves mathematically plotted rather than fluoresced"),
        ("thermocycler_internal_instrument_run_log.txt", "document", 35, "Needs review", "Run terminated at cycle 18 rather than standard 40 cycles"),
    ]),
    ("MED-2024-8083", "Veterinary Vaccine Cold Chain Temperature Sensor Override", "Nida Shaikh", [
        ("refrigerated_cargo_temp_logger_export.csv", "document", 27, "Likely manipulated", "Constant 4.0C temperature logged during 18-hour power failure"),
        ("reefer_truck_engine_telematics_obd.csv", "document", 88, "Consistent", "Refrigeration auxiliary unit alternator off during entire transit leg"),
    ]),
    ("MED-2024-8092", "Medical Malpractice Electronic Health Record Retroactive Chart Scrubbing", "Krishna Deshmukh", [
        ("epic_systems_ehr_audit_trail_timeline.json", "document", 19, "Likely manipulated", "Physician order notes created 3 days post-event backdated to admission time"),
        ("vital_signs_telemetry_nursing_flowsheet.pdf", "document", 94, "Consistent", "Nursing vital signs flowsheet unaltered, showing critical hypotension"),
    ]),

    # 81-90: Aviation, Maritime, Space & Transport Telemetry
    ("AVN-2024-9011", "Commercial Airliner Flight Data Recorder Altitude Splice & Forgery", "Insp. Meera Kulkarni", [
        ("fdr_blackbox_binary_telemetry_dump.dat", "document", 14, "Likely manipulated", "Pitot-static pressure sensor frame overwritten with synthetic glidepath"),
        ("cockpit_voice_recorder_cvr_audio_4ch.wav", "audio", 95, "Consistent", "Four-channel cockpit microphone audio authenticated with 400Hz aircraft AC hum"),
    ]),
    ("AVN-2024-9020", "International Container Cargo Ship AIS Collision Avoidance Spoofing", "SI Rohan Patil", [
        ("vessel_automatic_identification_system_nmea.log", "document", 21, "Likely manipulated", "AIS transponder broadcast false GPS coordinates 12 nm off true position"),
        ("coastal_vessel_traffic_service_radar_plot.png", "image", 93, "Consistent", "Shore-based X-band primary radar confirms actual vessel trajectory"),
    ]),
    ("AVN-2024-9029", "Commercial Drone Airspace Intrusion Near Presidential Helicopter", "Krishna Deshmukh", [
        ("dji_aeroscope_drone_rf_detection_log.json", "document", 94, "Consistent", "AeroScope RF telemetry verified with drone serial number and pilot remote ID"),
        ("pilot_smartphone_flight_app_cache.db", "document", 91, "Consistent", "Extracted SQLite database confirms NFZ geofence bypass hack installed"),
    ]),
    ("AVN-2024-9038", "Autonomous Commercial Electric Freight Truck Autopilot Sensor Tamper", "Kavya Rao", [
        ("lidar_pointcloud_camera_fusion_telemetry.bag", "document", 18, "Likely manipulated", "Laser return reflection points deleted in perception buffer prior to impact"),
        ("truck_chassis_can_bus_diagnostic_dump.csv", "document", 92, "Consistent", "CAN bus data corroborates zero braking command issued by AI planner"),
    ]),
    ("AVN-2024-9047", "Commercial Satellite Orbital Collision Maneuver Command Injection", "Insp. Meera Kulkarni", [
        ("satellite_telemetry_tracking_and_command_log.bin", "document", 25, "Likely manipulated", "Reaction wheel angular momentum forced into saturation via malicious command"),
        ("space_surveillance_network_optical_track.fits", "image", 96, "Consistent", "Ground telescope optical tracking confirms anomalous tumbling rotation"),
    ]),
    ("AVN-2024-9056", "High-Speed Passenger Ferry Engine Room Automation Sensor Hijack", "SI Rohan Patil", [
        ("marine_diesel_engine_alarm_monitoring_log.csv", "document", 28, "Likely manipulated", "Lube oil pressure alarm threshold muted in programmable automation controller"),
        ("crankcase_explosion_relief_valve_photo.jpg", "image", 95, "Consistent", "Mechanical thermal discoloration confirms bearing seizure without alarm"),
    ]),
    ("AVN-2024-9065", "Air Traffic Control Audio Dispatch Voice Recording Splicing", "Insp. Meera Kulkarni", [
        ("atc_tower_approach_clearance_radio.wav", "audio", 16, "Likely manipulated", "Clearance to land' audio segment spliced from earlier flight recording"),
        ("ground_radar_asde_x_runway_motion_track.mp4", "video", 94, "Consistent", "Airport surface detection equipment radar proves runway was occupied"),
    ]),
    ("AVN-2024-9074", "Commercial Helicopter Rotor Blade Fatigue Crack Non-Destructive Test", "Nida Shaikh", [
        ("eddy_current_ultrasonic_ndt_inspection_report.pdf", "document", 22, "Likely manipulated", "A-scan oscilloscope signal waveform copied from pristine blade baseline"),
        ("fractured_rotor_hub_metallurgical_macro.jpg", "image", 97, "Consistent", "Electron microscopy reveals textbook beachmark progressive fatigue striations"),
    ]),
    ("AVN-2024-9083", "Intercontinental Freight Rail EOT Telemetry Brake Dump Sabotage", "Krishna Deshmukh", [
        ("end_of_train_eot_device_rf_signal.bin", "document", 29, "Likely manipulated", "Emergency brake dump RF telegram transmitted on 457.9375 MHz without key"),
        ("locomotive_cab_display_snapshot.png", "image", 90, "Consistent", "Cab control screen captures sudden brake pipe pressure drop to 0 PSI"),
    ]),
    ("AVN-2024-9092", "General Aviation Experimental Aircraft Fuel Sensor Calibration Tamper", "SI Rohan Patil", [
        ("glass_cockpit_avionics_sdcard_data.csv", "document", 32, "Needs review", "Fuel quantity sender calibration curve modified to display 15 gallons when empty"),
        ("ntsb_wreckage_fuel_tank_inspection_photo.jpg", "image", 96, "Consistent", "Physical wreckage inspection proves zero usable fuel in header tanks"),
    ]),

    # 91-100: Intellectual Property, Industrial Espionage & Military Defense
    ("IP-2024-1001", "Aerospace Contractor Hypersonic Glide Vehicle CAD Blueprint Exfiltration", "Insp. Meera Kulkarni", [
        ("hypersonic_leading_edge_thermal_cad.step", "document", 89, "Consistent", "Authentic 3D boundary representation of carbon-carbon thermal TPS design"),
        ("insider_threat_dlp_usb_transfer_log.csv", "document", 94, "Consistent", "Symantec DLP agent confirms 18.4GB transferred to unapproved Kingston USB"),
    ]),
    ("IP-2024-1010", "Semiconductor Extreme Ultraviolet (EUV) Photolithography Mirror Leak", "Krishna Deshmukh", [
        ("euv_multipolar_optics_interferometry_data.dat", "document", 91, "Consistent", "Sub-nanometer wavefront measurement files verified with ASML test bench"),
        ("encrypted_telegram_channel_leak_export.json", "document", 87, "Consistent", "Broker communication matches darknet broker moniker selling IP"),
    ]),
    ("IP-2024-1019", "Automotive Solid-State Battery Electrolyte Chemical Formula Theft", "SI Rohan Patil", [
        ("sulfide_solid_electrolyte_synthesis_patent.docx", "document", 19, "Likely manipulated", "Chemical stoichiometry modified in Word track-changes to conceal theft"),
        ("rd_chemist_laboratory_notebook_scan.pdf", "document", 95, "Consistent", "Original signed notebook pages verify legitimate company priority invention"),
    ]),
    ("IP-2024-1028", "Pharmaceutical Multi-Billion Weight-Loss Peptide Synthesis Method", "Insp. Meera Kulkarni", [
        ("solid_phase_peptide_synthesizer_run.csv", "document", 92, "Consistent", "High-throughput synthesizer protocol commands for GLP-1 agonist formulation"),
        ("former_vp_laptop_forensic_image_en01.E01", "document", 97, "Consistent", "FTK forensic image recovers deleted cloud backup archive from Slack"),
    ]),
    ("IP-2024-1037", "Defense AI Autonomous Swarm Drone Neural Network Weights Exfiltration", "Krishna Deshmukh", [
        ("drone_swarm_rl_policy_weights.onnx", "document", 88, "Consistent", "PyTorch trained tensor parameters for multi-agent reinforcement swarm tactics"),
        ("github_private_repo_git_reflog.txt", "document", 93, "Consistent", "Git reflog confirms push to unauthorized external mirror before credentials revoked"),
    ]),
    ("IP-2024-1046", "High-Yield Quantum Computing Superconducting Qubit Resonator Design", "Kavya Rao", [
        ("transmon_qubit_ansys_hfss_simulation.hfss", "document", 90, "Consistent", "Microwave resonator frequency simulation verified with dilution fridge logs"),
        ("cleanroom_wafers_dicing_specifications.pdf", "document", 85, "Consistent", "Wafer fab run card correlates with exfiltrated geometry dimensions"),
    ]),
    ("IP-2024-1055", "Proprietary Quantitative Arbitrage Trading Strategy Algorithm Theft", "SI Rohan Patil", [
        ("statistical_arbitrage_execution_engine.cpp", "document", 94, "Consistent", "Low-latency C++20 execution engine matching proprietary trading firm codebase"),
        ("aws_s3_bucket_access_cloudtrail_log.json", "document", 96, "Consistent", "CloudTrail logs confirm S3 GetObject call from employee residential IP"),
    ]),
    ("IP-2024-1064", "Agricultural Biotech Drought-Resistant GMO Corn Genome Sequence", "Nida Shaikh", [
        ("crispr_cas9_gene_knockout_fasta_sequence.fa", "document", 89, "Consistent", "Sequenced FASTA alignment confirms exact matching edited exon target"),
        ("greenhouse_trial_phenotype_photos.tar", "document", 91, "Consistent", "Photographic documentation of drought tolerance phenotype trials"),
    ]),
    ("IP-2024-1073", "Naval Submarine Acoustic Anechoic Tile Coating Formulation Exfiltration", "Insp. Meera Kulkarni", [
        ("polyurethane_acoustic_tile_rheology_report.pdf", "document", 21, "Likely manipulated", "Sonar absorption coefficients fabricated to mimic compliant specification"),
        ("drydock_hull_installation_telemetry.csv", "document", 87, "Consistent", "Actual drydock pressure sensor data confirms anechoic adhesive debonding"),
    ]),
    ("IP-2024-1082", "Space Launch Vehicle Methane Rocket Engine Turbopump Blueprint", "Krishna Deshmukh", [
        ("methalox_turbopump_impeller_cfd_simulation.cgns", "document", 93, "Consistent", "Computational fluid dynamics simulation of cryogenic rocket turbopump"),
        ("foreign_intelligence_handler_signal_chat.txt", "document", 89, "Consistent", "Signal messenger forensic extraction confirms espionage transmission"),
    ]),
]

def generate_stored_file(stored_name: str, media_type: str):
    """Ensure a physical file exists in UPLOAD_DIR for realistic testing/downloads."""
    dest = config.UPLOAD_DIR / stored_name
    if dest.exists() and dest.stat().st_size > 0:
        return
    
    # Generate realistic content based on media type
    if media_type == "document":
        content = f"%PDF-1.7\n%Evidence Integrity Platform Forensic Export File\n%Stored name: {stored_name}\n%Generated for integrity verification\n%%EOF".encode("utf-8")
    elif media_type == "image":
        # Minimal 1x1 valid PNG
        content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
    elif media_type == "audio":
        # Minimal valid WAV header
        content = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    elif media_type == "video":
        # Minimal MP4 container box header
        content = b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free\x00\x00\x00\x08mdat'
    else:
        content = f"FORENSIC EVIDENCE DUMP: {stored_name}\nSTATUS: VERIFIED\n".encode("utf-8")

    dest.write_bytes(content)

def seed_100_cases():
    init_db()
    db = SessionLocal()

    # Get all existing users
    all_users = db.query(User).all()
    if not all_users:
        print("Error: No users found in database. Run create_user first.")
        return

    print(f"Assigning cases to all {len(all_users)} user profiles: {[u.username for u in all_users]}")

    base_date = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    cases_added = 0
    evidence_added = 0

    for idx, (ref, title, lead_inv, ev_list) in enumerate(CASE_TEMPLATES):
        # Check if case reference already exists
        existing = db.query(Case).filter(Case.reference == ref).first()
        if existing:
            c = existing
        else:
            case_date = (base_date + timedelta(days=idx * 2, hours=random.randint(1, 14), minutes=random.randint(5, 50))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            c = Case(
                reference=ref,
                title=title,
                investigator=lead_inv,
                created_at=case_date,
            )
            db.add(c)
            db.flush()
            cases_added += 1

        # Associate ALL user profiles as members of this case
        for u in all_users:
            mem = db.query(CaseMember).filter(CaseMember.case_id == c.id, CaseMember.user_id == u.id).first()
            if not mem:
                role = "lead" if u.full_name == lead_inv or u.role == "admin" else "member"
                db.add(CaseMember(case_id=c.id, user_id=u.id, role=role, added_at=c.created_at))

        # Add evidence files for this case
        for ev_idx, (fn, mtype, score, verdict, finding_detail) in enumerate(ev_list):
            existing_ev = db.query(Evidence).filter(Evidence.case_id == c.id, Evidence.filename == fn).first()
            if existing_ev:
                continue

            # Deterministic SHA-256 for realism
            seed_bytes = f"{ref}_{fn}_{score}_{mtype}".encode("utf-8")
            sha256 = hashlib.sha256(seed_bytes).hexdigest()
            stored_name = f"{sha256[:16]}_{fn}"

            generate_stored_file(stored_name, mtype)
            file_size = (config.UPLOAD_DIR / stored_name).stat().st_size

            # Compute category scores based on overall score
            meta_s = max(0, min(100, score + random.randint(-8, 8)))
            cont_s = max(0, min(100, score + random.randint(-10, 10)))
            ai_s = max(0, min(100, score + random.randint(-12, 6)))
            aud_s = max(0, min(100, score + random.randint(-6, 12)))
            breakdown = json.dumps({
                "metadata": meta_s,
                "container": cont_s,
                "ai": ai_s,
                "audio": aud_s
            })

            details = json.dumps({
                "format": fn.split(".")[-1],
                "sha256": sha256,
                "media_type": mtype,
                "forensic_status": "Verified analysis complete",
                "integrity_level": "High" if score >= 75 else ("Medium" if score >= 40 else "Compromised"),
            })

            tags = json.dumps([
                mtype,
                ref.split("-")[0].lower(),
                "investigation",
                "tampered" if score < 40 else ("reviewed" if score < 75 else "authentic")
            ])

            ev = Evidence(
                case_id=c.id,
                filename=fn,
                stored_name=stored_name,
                media_type=mtype,
                size=file_size,
                sha256=sha256,
                status="done",
                stage="Complete",
                progress=100,
                score=score,
                verdict=verdict,
                breakdown=breakdown,
                details=details,
                report=f"Forensic Integrity Examination Report\nTarget File: {fn}\nSHA-256: {sha256}\nVerdict: {verdict} (Score: {score}/100)\n\nFinding Summary:\n{finding_detail}",
                report_model="Deterministic Forensics v2.4",
                review_status="reviewed" if score >= 75 else "pending",
                tags=tags,
                received_at=c.created_at,
                uploaded_by=lead_inv,
            )
            db.add(ev)
            db.flush()
            evidence_added += 1

            # Add primary forensic finding
            severity = "high" if score < 40 else ("medium" if score < 75 else "info")
            f = Finding(
                evidence_id=ev.id,
                category="metadata" if mtype in ["document", "image"] else "container",
                check="integrity_audit",
                severity=severity,
                penalty=100 - score,
                title=f"{verdict}: {fn}",
                detail=finding_detail,
                location=json.dumps({"offset": "0x00000420", "component": "header"}),
            )
            db.add(f)

            # Add Chain of Custody events
            c1 = CustodyEvent(
                evidence_id=ev.id,
                seq=1,
                action="Received & Logged",
                actor=lead_inv,
                at=c.created_at,
                file_hash=sha256,
                prev_hash="0000000000000000000000000000000000000000000000000000000000000000",
                event_hash=hashlib.sha256(f"{sha256}_received".encode("utf-8")).hexdigest(),
                note=f"Seized and ingested into forensic custody repository: {fn}",
            )
            c2 = CustodyEvent(
                evidence_id=ev.id,
                seq=2,
                action="Cryptographic Hash Verified",
                actor="System Verifier Daemon",
                at=c.created_at,
                file_hash=sha256,
                prev_hash=c1.event_hash,
                event_hash=hashlib.sha256(f"{c1.event_hash}_verified".encode("utf-8")).hexdigest(),
                note="SHA-256 integrity match verified against initial intake checksum.",
            )
            db.add_all([c1, c2])

    db.commit()
    total_cases = db.query(Case).count()
    total_ev = db.query(Evidence).count()
    print(f"Successfully finished seeding! Cases added: {cases_added}, Evidence added: {evidence_added}")
    print(f"Total cases in DB: {total_cases}, Total evidence items: {total_ev}")
    db.close()

if __name__ == "__main__":
    seed_100_cases()
