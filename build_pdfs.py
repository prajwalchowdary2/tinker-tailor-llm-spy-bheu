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
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1A2B4C'),
        spaceAfter=15
    )
    
    body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=18,
        spaceAfter=10
    )
    
    bold_body_style = ParagraphStyle(
        'SlideBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=18,
        spaceAfter=10
    )

    story = []

    # Slide 1: Title
    story.append(Paragraph("Tinker Tailor LLM Spy", title_style))
    story.append(Paragraph("Reconstructing 'Deleted' Chats & Hijacking Sessions from Chromium LevelDB Caches", ParagraphStyle('Sub', parent=title_style, fontSize=16, leading=20, textColor=colors.HexColor('#333333'))))
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Target Venue:</b> Black Hat Europe Briefings", body_style))
    story.append(Paragraph("<b>Authors:</b> Dr. Sapna V M, Prajwal Chowdary, Prasad H B", body_style))
    story.append(Paragraph("<b>Institution:</b> Dept of Computer Science & Engineering, PES University, Bangalore, India", body_style))
    story.append(Paragraph(f"<b>Official Repository:</b> <font color='#0066CC'>{REPO_URL}</font>", body_style))
    story.append(PageBreak())

    # Slide 2: Problem Statement
    story.append(Paragraph("I. Introduction & Ephemeral AI Fallacy", title_style))
    story.append(Paragraph("• <b>Cloud Deletion vs Local Persistence:</b> When users click 'Delete Chat' in ChatGPT, Claude, Gemini, or Perplexity, cloud backends mark records for deletion, but local endpoints retain serialized traces.", body_style))
    story.append(Paragraph("• <b>LSM-Tree Storage Engine Mechanics:</b> Chromium browsers (Chrome, Edge) backed by LevelDB write telemetry sequentially to Write-Ahead Logs (.log) and uncompacted Sorted String Tables (.sst/.ldb).", body_style))
    story.append(Paragraph("• <b>Forensic Window:</b> Until background LSM compaction occurs (which may take hours or days), 'deleted' prompts and credentials remain fully recoverable on local disk.", body_style))
    story.append(PageBreak())

    # Slide 3: V8 Deserialization
    story.append(Paragraph("II. Low-Level V8 Deserialization Architecture", title_style))
    story.append(Paragraph("• <b>Varint Decoding:</b> Protocol Buffer style variable-length integers where bit 7 indicates continuation.", body_style))
    story.append(Paragraph("• <b>V8 String Tags:</b> OneByteString (0x22 ASCII) and TwoByteString (0x63 UTF-16LE byte-length tagged parsing).", body_style))
    story.append(Paragraph("• <b>Smi-Shifted Array Keys:</b> Small Integer (Smi) array indices encoded via left-shift (encoded = actual << 1). Odd actual indices represent User prompts; even actual indices represent Assistant responses.", body_style))
    story.append(Paragraph("• <b>Nesting Depth Tracking:</b> Dynamic tracking of object/array depth (0x6f/0x61) to prevent premature object termination on inner tags (0x7b).", body_style))
    story.append(PageBreak())

    # Slide 4: Real-Time DLP & Forensics
    story.append(Paragraph("III. Live Carving & Shadow AI DLP Engine", title_style))
    story.append(Paragraph("• <b>File Lock Bypass:</b> Read-only binary stream extraction prevents database lock collisions on active user sessions.", body_style))
    story.append(Paragraph("• <b>Multi-Profile Traversal:</b> Automatically walking Default and secondary profile paths (Profile 1, Profile 2, etc.).", body_style))
    story.append(Paragraph("• <b>Real-Time DLP Engine:</b> On-the-fly regex pattern scanning for leaked AWS keys, OpenAI API tokens, Slack tokens, and PII.", body_style))
    story.append(Paragraph("• <b>Cryptographic Chain of Custody:</b> Client-side Web Cryptography API HMAC-SHA256 evidence verification.", body_style))
    story.append(PageBreak())

    # Slide 5: Threat Vector Benchmark
    story.append(Paragraph("IV. 41ms Infostealer Threat Vector PoC", title_style))
    story.append(Paragraph("• <b>Headless Execution PoC (verity_stealer.py):</b> Headless Python script demonstrating sub-50ms harvesting of local LLM telemetry.", body_style))
    story.append(Paragraph("• <b>Bypassing EDR Alerts:</b> Demonstrates how rapid memory/file read execution occurs before traditional endpoint heuristic alerts trigger.", body_style))
    story.append(Paragraph("• <b>Multi-Application Scope:</b> Extracts from Chromium LevelDB, Claude TipTap draft keystrokes, Cursor IDE agent transcripts, and VS Code Copilot SQLite databases.", body_style))
    story.append(PageBreak())

    # Slide 6: Conclusion & Mitigations
    story.append(Paragraph("V. Conclusion & Defensive Mitigations", title_style))
    story.append(Paragraph("• <b>Enforce Encryption:</b> Apply OS-level cryptographic protections (DPAPI / FileVault / BitLocker) to browser IndexedDB LevelDB paths.", body_style))
    story.append(Paragraph("• <b>Browser Eviction Policies:</b> Configure MDM/GPO clean-up policies for local LevelDB databases on exit.", body_style))
    story.append(Paragraph("• <b>EDR Telemetry Monitoring:</b> Monitor unprivileged processes accessing Chromium profile paths.", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"• <b>Open-Source Tool Release:</b> The complete Tinker Tailor LLM Spy framework is available on GitHub:<br/><font color='#0066CC'><b>{REPO_URL}</b></font>", bold_body_style))

    doc.build(story)

def create_research_paper(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Times-Bold', fontSize=18, leading=22, alignment=1, spaceAfter=12)
    authors_style = ParagraphStyle('DocAuthors', parent=styles['Normal'], fontName='Times-Roman', fontSize=11, leading=14, alignment=1, spaceAfter=18)
    h2_style = ParagraphStyle('DocH2', parent=styles['Heading2'], fontName='Times-Bold', fontSize=13, leading=16, spaceBefore=12, spaceAfter=6)
    p_style = ParagraphStyle('DocP', parent=styles['Normal'], fontName='Times-Roman', fontSize=10, leading=14, spaceAfter=8)

    story = []
    story.append(Paragraph("Tinker Tailor LLM Spy: Reconstructing 'Deleted' Chats & Hijacking Sessions from Chromium LevelDB Caches", title_style))
    story.append(Paragraph("<b>Dr. Sapna V M, Prajwal Chowdary, Prasad H B</b><br/>Department of Computer Science & Engineering, PES University, Bangalore, India<br/><i>Target Venue: Black Hat Europe Briefings</i>", authors_style))
    
    story.append(Paragraph("Abstract", h2_style))
    story.append(Paragraph(f"As Large Language Model (LLM) portals become standard enterprise utilities, proprietary code and credentials are routinely processed by endpoints. When a user clicks 'Delete Chat' inside ChatGPT, Claude, or Gemini, cloud records are marked for removal, but local Chromium LevelDB storage retains write-ahead log records (.log) and uncompacted Sorted String Tables (.sst/.ldb). This paper introduces <b>Tinker Tailor LLM Spy</b>, a zero-dependency forensic framework to dissect V8 serialized binary structures, parse Smi-shifted array keys, and extract deleted LLM telemetry. Official open-source repository: {REPO_URL}", p_style))

    story.append(Paragraph("1. Introduction", h2_style))
    story.append(Paragraph("Digital forensics investigators face a critical blind spot in client-side Generative AI telemetry. Because LevelDB is an append-only log-structured merge-tree (LSM tree), deleted records persist until compaction. Our framework dissects raw binary streams directly from disk without database lock collisions.", p_style))

    story.append(Paragraph("2. Low-Level Database & V8 Architecture", h2_style))
    story.append(Paragraph("Chromium serializes IndexedDB values using V8 ValueSerializer. Lengths are encoded via Protocol Buffer varints. OneByteString (0x22) and TwoByteString (0x63 UTF-16LE) tags are decoded alongside Smi-shifted array keys (actual = encoded >> 1). Dynamic depth tracking ensures complete message reassembly.", p_style))

    story.append(Paragraph("3. Defensive Mitigations & Availability", h2_style))
    story.append(Paragraph(f"Mitigations include GPO/MDM cache eviction policies, BitLocker encryption, and EDR path monitoring. The open-source forensic tool and whitepaper are available at: {REPO_URL}", p_style))

    doc.build(story)

def create_research_poster(filename):
    doc = SimpleDocTemplate(filename, pagesize=landscape(letter),
                            leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('PosterTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, leading=24, alignment=1, spaceAfter=15)
    body_style = ParagraphStyle('PosterBody', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=16, spaceAfter=8)

    story = []
    story.append(Paragraph("TINKER TAILOR LLM SPY — RESEARCH POSTER", title_style))
    story.append(Paragraph("<b>PES University AI Forensics Lab | Black Hat Europe Briefings</b>", ParagraphStyle('Sub', parent=title_style, fontSize=13, leading=16)))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Key Breakthroughs:</b>", ParagraphStyle('H2', parent=body_style, fontName='Helvetica-Bold', fontSize=13)))
    story.append(Paragraph("1. Sub-50ms zero-dependency LevelDB SSTable and Write-Ahead Log carver.", body_style))
    story.append(Paragraph("2. Complete extraction of Claude TipTap draft keystrokes before submission.", body_style))
    story.append(Paragraph("3. V8 serialization varint and Smi-shifted array index key reassembly.", body_style))
    story.append(Paragraph("4. Real-time Shadow AI DLP credential detection and HMAC-SHA256 evidence integrity sealing.", body_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"<b>Official Codebase:</b> <font color='#0066CC'>{REPO_URL}</font>", body_style))

    doc.build(story)

def create_arsenal_proposal(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('PropTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, leading=20, spaceAfter=12)
    body_style = ParagraphStyle('PropBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=15, spaceAfter=8)

    story = []
    story.append(Paragraph("Black Hat Europe Arsenal Proposal: Tinker Tailor LLM Spy", title_style))
    story.append(Paragraph("<b>Presenter:</b> Prajwal Chowdary, Dr. Sapna V M, Prasad H B (PES University)", body_style))
    story.append(Paragraph("<b>Track:</b> Exploitation and Ethical Hacking / Incident Response / AI Security", body_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Tool Description:</b>", ParagraphStyle('H', parent=body_style, fontName='Helvetica-Bold')))
    story.append(Paragraph("Tinker Tailor LLM Spy is an open-source forensic carving and threat-hunting framework designed to recover deleted LLM chats, draft inputs, and session credentials from Chromium LevelDB storage.", body_style))
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
