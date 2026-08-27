import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
import os

doc = Document()

# Set standard margins
for section in doc.sections:
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_title(text, subtitle):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = 'Calibri'
    run.font.size = Pt(24)
    run.bold = True
    run.font.color.rgb = RGBColor(16, 44, 87)
    
    p2 = doc.add_paragraph()
    p2.paragraph_format.space_after = Pt(14)
    run2 = p2.add_run(subtitle)
    run2.font.name = 'Calibri'
    run2.font.size = Pt(12)
    run2.italic = True
    run2.font.color.rgb = RGBColor(100, 100, 100)

def add_h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Calibri'
    run.font.size = Pt(15)
    run.bold = True
    run.font.color.rgb = RGBColor(16, 44, 87)
    return p

def add_p(text, bold_prefix="", italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = 'Calibri'
        r_pre.font.size = Pt(10.5)
        r_pre.font.color.rgb = RGBColor(30, 30, 30)
    r = p.add_run(text)
    r.font.name = 'Calibri'
    r.font.size = Pt(10.5)
    r.italic = italic
    r.font.color.rgb = RGBColor(40, 40, 40)
    return p

def add_bullet(text, bold_prefix=""):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = 'Calibri'
        r_pre.font.size = Pt(10)
    r = p.add_run(text)
    r.font.name = 'Calibri'
    r.font.size = Pt(10)
    return p

def add_speech_box(time_range, title, spoken_lyrics, img_path=None):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.8)
    set_cell_background(cell, "F4F7FA")
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="12" w:space="0" w:color="1E56A0"/>
            <w:left w:val="single" w:sz="36" w:space="0" w:color="1E56A0"/>
            <w:bottom w:val="single" w:sz="12" w:space="0" w:color="1E56A0"/>
            <w:right w:val="single" w:sz="12" w:space="0" w:color="1E56A0"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    
    # Header
    r_hdr = p.add_run(f"⏱️ [{time_range}] — {title}\n")
    r_hdr.bold = True
    r_hdr.font.name = 'Calibri'
    r_hdr.font.size = Pt(12)
    r_hdr.font.color.rgb = RGBColor(16, 44, 87)
    
    # Spoken Lyrics with Inline Cues
    r_spk_hdr = p.add_run("🎙️ WORD-FOR-WORD SPOKEN SCRIPT WITH INLINE VISUAL & CODE CUES:\n")
    r_spk_hdr.bold = True
    r_spk_hdr.font.name = 'Calibri'
    r_spk_hdr.font.size = Pt(10.5)
    r_spk_hdr.font.color.rgb = RGBColor(16, 44, 87)
    
    # Format inline [SHOW: ...] and [ACTION: ...] tags nicely
    parts = spoken_lyrics.split("[")
    p_spk = cell.add_paragraph()
    p_spk.paragraph_format.space_after = Pt(4)
    p_spk.paragraph_format.line_spacing = 1.15
    
    for idx, pt in enumerate(parts):
        if idx == 0:
            r = p_spk.add_run(pt)
            r.font.name = 'Calibri'
            r.font.size = Pt(10.5)
            r.font.color.rgb = RGBColor(30, 30, 30)
        else:
            if "]" in pt:
                tag_content, text_content = pt.split("]", 1)
                r_tag = p_spk.add_run(f"[{tag_content}] ")
                r_tag.bold = True
                r_tag.font.name = 'Calibri'
                r_tag.font.size = Pt(9.5)
                if tag_content.startswith("SHOW CODE"):
                    r_tag.font.color.rgb = RGBColor(180, 50, 20) # Red/Orange for code
                elif tag_content.startswith("SHOW UI"):
                    r_tag.font.color.rgb = RGBColor(30, 86, 160) # Blue for UI
                elif tag_content.startswith("ACTION"):
                    r_tag.font.color.rgb = RGBColor(0, 120, 50) # Green for actions
                else:
                    r_tag.font.color.rgb = RGBColor(120, 40, 140)
                    
                r_txt = p_spk.add_run(text_content)
                r_txt.font.name = 'Calibri'
                r_txt.font.size = Pt(10.5)
                r_txt.font.color.rgb = RGBColor(30, 30, 30)
            else:
                r = p_spk.add_run("[" + pt)
                r.font.name = 'Calibri'
                r.font.size = Pt(10.5)
                r.font.color.rgb = RGBColor(30, 30, 30)
    
    # Image if available
    if img_path and os.path.exists(img_path):
        p_img = cell.add_paragraph()
        p_img.paragraph_format.space_before = Pt(6)
        p_img.paragraph_format.space_after = Pt(2)
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.add_run().add_picture(img_path, width=Inches(6.0))
        
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_after = Pt(6)

# Title
add_title("PO Backlog Architect Agent — Word-for-Word Presentation Script with Inline Screen & Code Cues", 
          "Complete Live Presentation Script ('Lyrics') with Integrated Screen Cues, VS Code Line References, and Embedded Screenshots for Digital T3 Submission")

add_p("This document is your complete word-for-word presentation script. As you speak each sentence out loud, the inline bracketed tags tell you exactly what to show on screen [SHOW UI: ...], what file and line to display in VS Code [SHOW CODE: ...], or what button to click [ACTION: ...].", bold_prefix="Presentation Setup & How to Use: ")

add_bullet("Do NOT use PowerPoint slides. Share your desktop screen with Streamlit UI (http://localhost:8501) on the left half and VS Code on the right half.", "Visual Setup: ")
add_bullet("Terminal 1 running uvicorn app.main:app --reload and Terminal 2 running streamlit run ui/dashboard.py.", "Pre-Demo Terminals: ")

add_bullet("BL-001...BL-020 = Backlog Item / Story ID (from data/backlog.json)", "📌 ID Naming Prefix Cheatsheet: ")
add_bullet("EP-001...EP-002 = Epic ID (from data/epics.json)", "  ")
add_bullet("PB-01...PB-15 = Product Brief Section Reference ID (from data/product_brief.md)", "  ")
add_bullet("DFT-001...DFT-005 = Generated Draft ID in Approval Queue (from database/service layer)", "  ")

img_dir = r"e:\Digital T3\po-backlog-architect-agent\docs\images"

# PART 1
add_h1("Part 1: 0:00 – 1:30 | Opening Pitch & Architecture Philosophy")
add_speech_box(
    time_range="0:00 – 1:30",
    title="The Opening Pitch & Governance Philosophy",
    spoken_lyrics=(
        "Hello everyone! Today I'm presenting the PO Backlog Architect Agent for FlowDesk. "
        "[SHOW UI: Streamlit Sidebar at http://localhost:8501 - LLM Provider Selector & Active Safeguards] "
        "Notice in our Streamlit sidebar that we support two LLM providers via our abstract LLMProvider protocol "
        "[SHOW CODE: app/llm/base.py: L1 - L30 (LLMProvider abstract protocol)]: "
        "GroqProvider using open-weights model qwen/qwen3.6-27b for live AI inference "
        "[SHOW CODE: app/llm/groq_provider.py: L1 - L85], "
        "and MockProvider for fast, 0.05-second deterministic offline testing "
        "[SHOW CODE: app/llm/mock_provider.py: L1 - L75]. "
        "When engineering teams try using LLMs to generate user stories and acceptance criteria, three major failure modes occur: "
        "First, hallucinated technical requirements—like an AI inventing a 50 MB file size limit when the specification has no exact number. "
        "Second, generic story proliferation—vague user stories like 'As a user, I want to manage data efficiently' that fail Definition of Ready. "
        "And third, uncontrolled external writes—where an LLM pushes unreviewed items directly into Jira or Azure DevOps as READY. "
        "Our core design philosophy is GOVERNANCE OVER GENERATION "
        "[SHOW CODE: README.md: L212 - L235 (Architecture Component Boundaries Diagram)]. "
        "The LLM proposes artifacts, but deterministic Python service code validates section-level citations, scores anti-generic specificity across 3 layers, "
        "evaluates Definition of Ready rules, and enforces a structural human approval gate with an immutable NOT_READY status floor."
    ),
    img_path=os.path.join(img_dir, "tab1_context_search.png")
)

# PART 2
add_h1("Part 2: 1:30 – 3:00 | Context Indexing (O1) & Epic Decomposition (O2)")
add_speech_box(
    time_range="1:30 – 3:00",
    title="Context Indexing (O1) & Epic Decomposition (O2)",
    spoken_lyrics=(
        "First, let's look at Context Indexing in Tab 1 "
        "[SHOW UI: Streamlit Tab 1 - Context Search (O1)]. "
        "We parse the FlowDesk product brief into 15 addressable sections, indexed with SQLite FTS5 "
        "[SHOW CODE: app/services/context_service.py: L15 - L65 (index_markdown_brief)]. "
        "If I search 'file upload' [ACTION: Type 'file upload' into search box and click 'Search Context'], "
        "the engine retrieves section PB-04.1. This addressable indexing is what enables claim-level citation validation.\n"
        "Now let me move to Tab 2: Epic Decomposition "
        "[SHOW UI: Streamlit Tab 2 - Epic Decomposer (O2)]. "
        "If I select EP-001—a detailed document management epic "
        "[SHOW CODE: data/epics.json: L1 - L8 (EP-001 definition) and ACTION: Select 'EP-001' and click 'Decompose Epic']—"
        "the agent generates structured stories with citations "
        "[SHOW CODE: app/agents/decomposition_agent.py: L20 - L80]. "
        "However, look at EP-002—a thin, 6-word epic titled 'Automate Approval Overrides' "
        "[SHOW CODE: data/epics.json: L9 - L16 (EP-002 thin epic) and ACTION: Select 'EP-002' and click 'Decompose Epic']. "
        "Instead of fabricating fake requirements, our decomposition agent detects that detail is missing and surfaces Open Questions to the Product Owner first, "
        "such as 'What role is authorized to perform overrides?'"
    ),
    img_path=os.path.join(img_dir, "tab2_epic_decomposer.png")
)

# PART 3
add_h1("Part 3: 3:00 – 4:30 | Acceptance Criteria (O3), Citations (O6) & Anti-Generic Guard (O8)")
add_speech_box(
    time_range="3:00 – 4:30",
    title="Acceptance Criteria, Citation Validation & Anti-Generic Guard",
    spoken_lyrics=(
        "In Tab 3, we generate Given/When/Then acceptance criteria "
        "[SHOW UI: Streamlit Tab 3 - Criteria Generator (O3/O6/O8)]. "
        "The UI pre-fills candidate story BL-006—'Upload Supporting Documents to Request' "
        "[ACTION: Review pre-filled Story Title & Description, then click 'Generate Acceptance Criteria']. "
        "When I click 'Generate Acceptance Criteria', the agent produces testable GWT scenarios and attaches verified citation PB-04.1. "
        "Our CitationService [SHOW CODE: app/services/citation_service.py: L30 - L95] checks both existence and numeric term grounding.\n"
        "Below, we have our 3-Layer Anti-Generic Guard [SHOW UI: Streamlit Tab 3 Lower Section]. "
        "If someone inputs a vague requirement like 'Manage my data efficiently' "
        "[ACTION: Type 'Manage my data efficiently' in custom text box and click 'Evaluate Specificity & Rewrite'], "
        "our guard evaluates 3 layers: Layer 1 exact phrase match ('manage data'), Layer 2 vague verb regex ('manage') "
        "[SHOW CODE: config/generic_guard.json: L1 - L35], "
        "and Layer 3 specificity score [SHOW CODE: app/services/generic_guard_service.py: L40 - L110]. "
        "It flags the story as GENERIC (Score = 1) and automatically rewrites it into a domain-specific user story with a measurable outcome."
    ),
    img_path=os.path.join(img_dir, "tab3_criteria_generator.png")
)

# PART 4
add_h1("Part 4: 4:30 – 6:00 | Readiness Gate (O4), Prioritization (O5) & Overlap Detector (O7)")
add_speech_box(
    time_range="4:30 – 6:00",
    title="Definition of Ready Gate, Formula Prioritization & Overlap Detector",
    spoken_lyrics=(
        "In Tab 4, we evaluate the Definition of Ready "
        "[SHOW UI: Streamlit Tab 4 - Readiness Gate (O4)]. "
        "Selecting BL-003 [ACTION: Select 'BL-003: Quick Search Tickets' from dropdown and click 'Evaluate Readiness']—"
        "which lacks acceptance criteria—fails rule check 'has_acceptance_criteria' "
        "[SHOW CODE: config/readiness.yaml: L1 - L32 and app/services/readiness_service.py: L25 - L75] "
        "and returns status BLOCKED. Selecting BL-005 [ACTION: Select 'BL-005: Multi-File Attachment Processing' and click 'Evaluate Readiness'] "
        "passes all 6 YAML rules and returns status READY.\n"
        "In Tab 5 [SHOW UI: Streamlit Tab 5 - Prioritization Engine (O5)], "
        "our Prioritization Engine automatically calculates scores on page load "
        "[SHOW CODE: app/services/prioritization_service.py: L30 - L80] "
        "using a transparent mathematical formula rendered right at the top—combining Business Value, Urgency, Risk Reduction, Strategic Alignment, Dependency Penalty, and Readiness Factor. "
        "We don't ask the LLM for priority; we compute it deterministically.\n"
        "In Tab 6 [SHOW UI: Streamlit Tab 6 - Overlap Detector (O7)], "
        "Overlap Detector [SHOW CODE: app/services/overlap_service.py: L20 - L70] "
        "checks candidate story BL-006 'Upload Supporting Documents' "
        "[ACTION: Review pre-filled New Story Title & Description, then click 'Check Backlog Overlap'] "
        "against existing backlog stories and identifies it as a SUBSET of story BL-001 with high confidence, recommending a merge."
    ),
    img_path=os.path.join(img_dir, "tab4_readiness_gate.png")
)

# PART 5
add_h1("Part 5: 6:00 – 7:30 | ⭐ The Killer Demo: Human Approval Gate & Status Floor (O9)")
add_speech_box(
    time_range="6:00 – 7:30",
    title="The Killer Demo: Human Approval Gate & Status Floor (O9)",
    spoken_lyrics=(
        "Now for our core safety control in Tab 7: The Human Approval Gate and Status Floor "
        "[SHOW UI: Streamlit Tab 7 - Approval Queue (O9)].\n"
        "Notice draft DFT-001 in the queue with status PENDING. "
        "If an external system or user attempts to write this unapproved draft directly to MockTracker, "
        "watch what happens when I click 'Write to Tracker' "
        "[ACTION 1: Click 'Write to Tracker' on PENDING draft]: "
        "The service layer rejects the call and returns HTTP 403 Forbidden: Draft must be APPROVED "
        "[SHOW CODE: app/services/approval_service.py: L72 (if draft.status != ApprovalStatus.APPROVED: raise ApprovalRequiredError)].\n"
        "Now, as the human Product Owner, I click 'Approve Draft' [ACTION 2: Click 'Approve Draft']. "
        "The status changes to APPROVED.\n"
        "Now I click 'Write to Tracker' again [ACTION 3: Click 'Write to Tracker']. "
        "The call succeeds with HTTP 200 OK. But look at MockTracker "
        "[SHOW CODE: app/services/approval_service.py: L90 - L115 (write_draft_to_tracker forcing status=NOT_READY)]: "
        "Even though the draft was approved, the status is forcibly locked at NOT_READY and tagged 'AI-drafted'. "
        "This guarantees that no AI item enters a sprint without final human PO review."
    ),
    img_path=os.path.join(img_dir, "tab7_approval_queue.png")
)

# PART 6
add_h1("Part 6: 7:30 – 9:00 | Empirical Evaluation Harness & Adversarial Proofs")
add_speech_box(
    time_range="7:30 – 9:00",
    title="Empirical Evaluation Harness & Adversarial Probes",
    spoken_lyrics=(
        "To prove our system is robust beyond UI demonstrations, we built an automated evaluation suite "
        "[SHOW UI: Switch focus to Terminal window].\n"
        "In Terminal, I run 'python -m eval.run --provider mock' "
        "[ACTION: Run 'python -m eval.run --provider mock' in Terminal and SHOW CODE: eval/run.py: L20 - L100]—"
        "achieving 10/10 PASS across all Golden Cases in 0.05 seconds.\n"
        "Next, running 'python eval/compare.py' "
        "[ACTION: Run 'python eval/compare.py' in Terminal and SHOW CODE: eval/compare.py: L10 - L60] "
        "benchmarks our deterministic Mock against live Groq LLM inference with qwen/qwen3.6-27b over 3 repeated runs. "
        "Groq achieves 10/10 PASS with 1.45-second average latency, zero retries, and zero schema failures.\n"
        "Finally, running 'python eval/adversarial_run.py' "
        "[ACTION: Run 'python eval/adversarial_run.py' in Terminal and SHOW CODE: eval/adversarial_run.py: L15 - L90] "
        "executes 7 adversarial probes—achieving 7/7 PASS. "
        "For example, ADV-01 injects a hallucinated '50 MB' file limit. CitationService detects that '50 MB' is not in PB-04.2 and rejects the claim."
    ),
    img_path=os.path.join(img_dir, "tab5_prioritization.png")
)

# PART 7
add_h1("Part 7: 9:00 – 10:00 | Architectural Trade-offs & Q&A Defense Strategy")
add_speech_box(
    time_range="9:00 – 10:00",
    title="Architectural Trade-offs & Q&A Defense",
    spoken_lyrics=(
        "In conclusion, our project evolved from a feature prototype into a governed AI Product Owner system.\n"
        "We made three key architectural decisions documented in our ADR log "
        "[SHOW CODE: docs/decision-log.md: L1 - L150]:\n"
        "First, we chose SQLite FTS5 over Vector DBs [SHOW CODE: docs/decision-log.md - ADR-002] "
        "because our product brief is structured into addressable sections (PB-01 to PB-15). FTS5 provides 100% deterministic lookup with zero vector infrastructure overhead.\n"
        "Second, we built MockProvider alongside GroqProvider [SHOW CODE: docs/decision-log.md - ADR-004] "
        "to enable fast, reproducible CI regression testing.\n"
        "And third, we enforced approval gating and status floors in Python service objects "
        "[SHOW CODE: docs/decision-log.md - ADR-006 & ADR-008] "
        "rather than complex graph frameworks, keeping the codebase clean, maintainable, and robust.\n"
        "Thank you! I am now ready for any technical questions."
    ),
    img_path=os.path.join(img_dir, "tab6_overlap_detector.png")
)

# Save Document
out_doc_path = r"e:\Digital T3\po-backlog-architect-agent\docs\PO_Backlog_Architect_Demo_Presentation_Script.docx"
root_doc_path = r"e:\Digital T3\po-backlog-architect-agent\PO_Backlog_Architect_Demo_Presentation_Script.docx"

doc.save(out_doc_path)
doc.save(root_doc_path)

print(f"Demo presentation docx successfully regenerated at: {out_doc_path} and {root_doc_path}")
