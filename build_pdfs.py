#!/usr/bin/env python3
import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

REPO_URL = "https://github.com/prajwalchowdary2/tinker-tailor-llm-spy-bheu"

def create_presentation_slides(filename):
    doc = SimpleDocTemplate(filename, pagesize=landscape(letter),
                            leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'SlideTitle',
        parent=styles['Heading1'],
        fontName='Times-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1A2B4C'),
        spaceAfter=12
    )
    
    body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        spaceAfter=8
    )
    
    bold_body_style = ParagraphStyle(
        'SlideBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=16,
        spaceAfter=8
    )

    story = []

    # Slide 1: Title
    story.append(Paragraph("Tinker Tailor LLM Spy", title_style))
    story.append(Paragraph("Reconstructing 'Deleted' Chats & Hijacking Sessions from Chromium LevelDB Caches", ParagraphStyle('Sub', parent=title_style, fontSize=15, leading=18, textColor=colors.HexColor('#333333'))))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Target Venue:</b> Black Hat Europe Briefings", body_style))
    story.append(Paragraph("<b>Authors:</b> Dr. Sapna V M, Prajwal Chowdary, Prasad H B", body_style))
    story.append(Paragraph("<b>Institution:</b> ISFCR Lab, Dept of Computer Science & Engineering, PES University, Bangalore, India", body_style))
    story.append(Paragraph(f"<b>Official Repository:</b> <font color='#0066CC'>{REPO_URL}</font>", body_style))
    story.append(PageBreak())

    # Slide 2: Problem Statement & Remanence
    story.append(Paragraph("I. The Ephemeral AI Fallacy & LSM-Tree Remanence", title_style))
    story.append(Paragraph("• <b>Cloud Deletion vs Local Persistence:</b> Clicking 'Delete Chat' updates cloud servers, but Chromium (Chrome, Edge, Brave) and Electron desktop apps retain local telemetry in LevelDB storage.", body_style))
    story.append(Paragraph("• <b>Append-Only LSM Engine:</b> Writes are appended sequentially to Write-Ahead Logs (.log). 'Deletions' are mere index updates or tombstones; serialized data blocks linger intact until background compaction.", body_style))
    story.append(Paragraph("• <b>Empirical Finding:</b> 506 text artifacts recovered across 23 profiles; <b>70.8% (358 artifacts) were already deleted from the web UI</b>. One artifact persisted for 83 days.", body_style))
    story.append(PageBreak())

    # Slide 3: V8 Deserialization Mechanics
    story.append(Paragraph("II. Reverse Engineering V8 Serialization & Framing", title_style))
    story.append(Paragraph("• <b>Varint Decoding:</b> Protocol Buffer style 7-bit variable-length integer parsing for offsets and string lengths.", body_style))
    story.append(Paragraph("• <b>Tag Identification:</b> Parsing OneByteString (0x22 ASCII) and TwoByteString (0x63 UTF-16LE byte-length tagged strings).", body_style))
    story.append(Paragraph("• <b>Smi-Shifted Array Keys:</b> Small Integer keys encoded via left-shift (encoded = actual << 1). Odd actual indices = User Prompts; Even actual indices = Assistant Replies.", body_style))
    story.append(Paragraph("• <b>Nesting Depth Tracking:</b> Dynamic tracking of object/array depth (0x6f/0x61) prevents premature message truncation on inner end tags (0x7b).", body_style))
    story.append(PageBreak())

    # Slide 4: Critical Vulnerabilities Uncovered
    story.append(Paragraph("III. New Endpoint Vulnerability Discoveries", title_style))
    story.append(Paragraph("• <b>Claude Pre-Submission Keystroke Caching:</b> TipTap editor state serializes in-flight keystrokes to disk in real-time <i>before</i> the user clicks 'Send'. 148 draft fragments recovered.", body_style))
    story.append(Paragraph("• <b>Plaintext Document Blobs (.indexeddb.blob/):</b> Uploaded 10MB PDF documents and proprietary code files stored completely unencrypted, surviving conversation deletion indefinitely.", body_style))
    story.append(Paragraph("• <b>ECDSA Private Keys in ChatGPT Desktop:</b> com.openai.atlas stores raw WebRTC ECDSA private keys (-----BEGIN PRIVATE KEY-----) in LevelDB logs alongside chat transcripts.", body_style))
    story.append(Paragraph("• <b>Google Gemini Extension (glic):</b> Stores conversation keys (BARD_EMBED_CHAT_STORAGE_KEY) in Local Storage LevelDB.", body_style))
    story.append(PageBreak())

    # Slide 5: Real-Time Forensics & DLP
    story.append(Paragraph("IV. Live Carving Engine & Shadow AI DLP", title_style))
    story.append(Paragraph("• <b>Lock-Free Live Carving:</b> Read-only binary stream parsing bypasses exclusive LevelDB process locks without disrupting active browser sessions.", body_style))
    story.append(Paragraph("• <b>Real-Time Shadow AI DLP:</b> On-the-fly extraction and regex classification of leaked AWS access keys, OpenAI API tokens, Slack tokens, JWTs, and PII.", body_style))
    story.append(Paragraph("• <b>HMAC-SHA256 Chain of Custody:</b> Canonical evidence payload signing, verified client-side using Web Cryptography API (window.crypto.subtle.verify).", body_style))
    story.append(Paragraph("• <b>Sub-150ms Performance:</b> Full multi-profile scan completes in 147–163 ms, executing before endpoint monitor latency windows.", body_style))
    story.append(PageBreak())

    # Slide 6: Defensive Mitigations
    story.append(Paragraph("V. Defensive Mitigations & Tool Release", title_style))
    story.append(Paragraph("• <b>OS Storage Encryption:</b> Enforce full-disk encryption (FileVault / BitLocker) and extend DPAPI protections to IndexedDB storage directories.", body_style))
    story.append(Paragraph("• <b>Session Purge Policies:</b> Configure enterprise GPO/MDM browser policies to purge IndexedDB cache and blob files on browser termination.", body_style))
    story.append(Paragraph("• <b>Endpoint Telemetry Rules:</b> Deploy EDR behavioral rules monitoring unprivileged access to Chromium IndexedDB directories.", body_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"• <b>Complete Open-Source Release:</b> <br/><font color='#0066CC'><b>{REPO_URL}</b></font>", bold_body_style))

    doc.build(story)

def create_research_paper(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Times-Bold', fontSize=16, leading=20, alignment=1, spaceAfter=10)
    authors_style = ParagraphStyle('DocAuthors', parent=styles['Normal'], fontName='Times-Roman', fontSize=10, leading=13, alignment=1, spaceAfter=14)
    h2_style = ParagraphStyle('DocH2', parent=styles['Heading2'], fontName='Times-Bold', fontSize=12, leading=15, spaceBefore=10, spaceAfter=4)
    p_style = ParagraphStyle('DocP', parent=styles['Normal'], fontName='Times-Roman', fontSize=9.5, leading=13, spaceAfter=6)

    story = []
    story.append(Paragraph("Tinker Tailor LLM Spy: Reconstructing 'Deleted' Chats & Hijacking Sessions from Chromium LevelDB Caches", title_style))
    story.append(Paragraph("<b>Dr. Sapna V M, Prajwal Chowdary, Prasad H B</b><br/>ISFCR Lab, Department of Computer Science & Engineering, PES University, Bangalore, India<br/><i>Target Venue: Black Hat Europe Briefings</i>", authors_style))
    
    story.append(Paragraph("Abstract", h2_style))
    story.append(Paragraph(f"When users click 'Delete Chat' inside ChatGPT, Claude, or Gemini interfaces, cloud records are marked for removal, but local Chromium LevelDB storage retains write-ahead log records (.log), uncompacted SSTables (.ldb), and unencrypted blob files (.indexeddb.blob/). Across 23 browser profiles, we recovered 506 text artifacts, 70.8% of which had already been deleted from the UI. We also uncover pre-submission keystroke draft persistence in Claude TipTap, unencrypted 10MB PDF document blob persistence, and raw WebRTC ECDSA private keys in ChatGPT Desktop. We introduce <b>Tinker Tailor LLM Spy</b>, a zero-dependency, sub-150ms forensic framework. Official repository: {REPO_URL}", p_style))

    story.append(Paragraph("1. Introduction & The Ephemeral AI Fallacy", h2_style))
    story.append(Paragraph("Client-side Generative AI telemetry is a critical blind spot in endpoint security. Because LevelDB is an append-only LSM tree, deleted records persist until compaction. Our lock-free carver reconstructs conversations, keystroke drafts, and uploaded document attachments directly from raw binary streams.", p_style))

    story.append(Paragraph("2. Critical Vulnerability Discoveries", h2_style))
    story.append(Paragraph("• <b>LevelDB LSM Remanence:</b> 70.8% of recovered chat artifacts were UI-deleted, persisting up to 83 days.<br/>• <b>TipTap Keystroke Drafts:</b> In-flight prompt drafts are cached before clicking Send.<br/>• <b>Plaintext Document Blobs:</b> Uploaded PDFs and code files persist unencrypted in blob storage.<br/>• <b>Desktop App Key Exposure:</b> ChatGPT Desktop persists ECDSA private keys in LevelDB WAL logs.", p_style))

    story.append(Paragraph("3. Defensive Mitigations & Tool Release", h2_style))
    story.append(Paragraph(f"Mitigations include GPO cache eviction policies, BitLocker/FileVault encryption, and EDR path monitoring. The open-source forensic tool, whitepaper, and reproduction suites are available at: {REPO_URL}", p_style))

    doc.build(story)

def create_research_poster(filename):
    doc = SimpleDocTemplate(filename, pagesize=landscape(letter),
                            leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('PosterTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, alignment=1, spaceAfter=12)
    body_style = ParagraphStyle('PosterBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10.5, leading=15, spaceAfter=6)

    story = []
    story.append(Paragraph("TINKER TAILOR LLM SPY — RESEARCH POSTER", title_style))
    story.append(Paragraph("<b>PES University ISFCR Lab | Black Hat Europe Briefings</b>", ParagraphStyle('Sub', parent=title_style, fontSize=12, leading=15)))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Core Vulnerability Breakthroughs:</b>", ParagraphStyle('H2', parent=body_style, fontName='Helvetica-Bold', fontSize=12)))
    story.append(Paragraph("1. <b>LevelDB LSM Remanence:</b> 506 artifacts recovered; 70.8% UI-deleted; 83-day persistence.", body_style))
    story.append(Paragraph("2. <b>Claude TipTap Keystroke Caching:</b> Unsubmitted draft keystrokes captured before sending.", body_style))
    story.append(Paragraph("3. <b>Unencrypted Document Blobs:</b> 10MB PDFs and code attachments stored plaintext on disk.", body_style))
    story.append(Paragraph("4. <b>ChatGPT Desktop Key Exposure:</b> ECDSA private keys stored plaintext in LevelDB logs.", body_style))
    story.append(Paragraph("5. <b>Zero-Dependency Live Engine:</b> Sub-150ms full-profile scan with HMAC-SHA256 evidence sealing.", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Official Codebase & Whitepaper:</b> <font color='#0066CC'>{REPO_URL}</font>", body_style))

    doc.build(story)

def create_arsenal_proposal(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('PropTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, leading=20, spaceAfter=12)
    body_style = ParagraphStyle('PropBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=15, spaceAfter=8)

    story = []
    story.append(Paragraph("Black Hat Europe Arsenal Proposal: Tinker Tailor LLM Spy", title_style))
    story.append(Paragraph("<b>Presenter:</b> Prajwal Chowdary, Dr. Sapna V M, Prasad H B (PES University ISFCR)", body_style))
    story.append(Paragraph("<b>Track:</b> Exploitation and Ethical Hacking / Incident Response / AI Security", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Tool Description:</b>", ParagraphStyle('H', parent=body_style, fontName='Helvetica-Bold')))
    story.append(Paragraph("Tinker Tailor LLM Spy is an open-source forensic carving and threat-hunting framework designed to recover deleted LLM chats, pre-submission keystroke drafts, unencrypted document blobs, and session credentials from Chromium LevelDB storage.", body_style))
    story.append(Paragraph(f"<b>GitHub Repository:</b> {REPO_URL}", body_style))

    doc.build(story)

if __name__ == '__main__':
    print("[*] Generating updated PDFs with URL:", REPO_URL)
    create_presentation_slides("presentation_slides.pdf")
    create_presentation_slides("docs/presentation_slides.pdf")
    create_research_paper("docs/Tinker_Tailor_LLM_Spy_Paper.pdf")
    create_research_poster("research_poster.pdf")
    create_research_poster("docs/research_poster.pdf")
    create_arsenal_proposal("docs/BlackHat_Europe_Arsenal_Proposal.pdf")
    print("[+] All PDF files generated successfully!")
