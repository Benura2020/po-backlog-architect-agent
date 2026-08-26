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
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

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
    run.font.size = Pt(26)
    run.bold = True
    run.font.color.rgb = RGBColor(16, 44, 87)
    
    p2 = doc.add_paragraph()
    p2.paragraph_format.space_after = Pt(18)
    run2 = p2.add_run(subtitle)
    run2.font.name = 'Calibri'
    run2.font.size = Pt(13)
    run2.italic = True
    run2.font.color.rgb = RGBColor(100, 100, 100)

def add_h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Calibri'
    run.font.size = Pt(18)
    run.bold = True
    run.font.color.rgb = RGBColor(16, 44, 87)
    return p

def add_h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Calibri'
    run.font.size = Pt(14)
    run.bold = True
    run.font.color.rgb = RGBColor(30, 86, 160)
    return p

def add_h3(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Calibri'
    run.font.size = Pt(12)
    run.bold = True
    run.font.color.rgb = RGBColor(50, 50, 50)
    return p

def add_p(text, bold_prefix="", italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = 'Calibri'
        r_pre.font.size = Pt(11)
        r_pre.font.color.rgb = RGBColor(30, 30, 30)
    r = p.add_run(text)
    r.font.name = 'Calibri'
    r.font.size = Pt(11)
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
        r_pre.font.size = Pt(10.5)
    r = p.add_run(text)
    r.font.name = 'Calibri'
    r.font.size = Pt(10.5)
    return p

def add_callout(title, text, bg_hex="F0F4F8", border_hex="1E56A0"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.8)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:left w:val="single" w:sz="36" w:space="0" w:color="{border_hex}"/>
            <w:bottom w:val="none"/>
            <w:right w:val="none"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    r1 = p.add_run(f"💡 {title}\n")
    r1.bold = True
    r1.font.name = 'Calibri'
    r1.font.size = Pt(11)
    r1.font.color.rgb = RGBColor(16, 44, 87)
    
    r2 = p.add_run(text)
    r2.font.name = 'Calibri'
    r2.font.size = Pt(10)
    r2.font.color.rgb = RGBColor(40, 40, 40)
    
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_after = Pt(4)

def add_styled_table(headers, rows_data):
    tbl = doc.add_table(rows=len(rows_data) + 1, cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    hdr_cells = tbl.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        set_cell_background(hdr_cells[i], "1E56A0")
        set_cell_margins(hdr_cells[i], top=100, bottom=100, left=120, right=120)
        p = hdr_cells[i].paragraphs[0]
        for r in p.runs:
            r.font.name = 'Calibri'
            r.font.size = Pt(10)
            r.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            
    for r_idx, row in enumerate(rows_data):
        row_cells = tbl.rows[r_idx + 1].cells
        bg = "F9FBFD" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            for r in p.runs:
                r.font.name = 'Calibri'
                r.font.size = Pt(9.5)
                r.font.color.rgb = RGBColor(40, 40, 40)
                
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_after = Pt(6)

# Document Header
add_title("PO Backlog Architect Agent — Master Guide & Knowledge Document", 
          "Complete Engineering Reference, Architectural Decision Record, Code Map, Testing Evidence, and Demo Study Guide for Digital T3 Submission")

add_callout("Master Reference Document Purpose", 
            "This document is designed as a single, comprehensive reference for the FlowDesk PO Backlog Architect Agent system. "
            "It covers every aspect of the project: business problem, system architecture, 8 key Architectural Decision Records (ADRs), file-by-file code map, "
            "eval & testing evidence (10/10 Golden Cases, 7/7 Adversarial Probes), tech stack, marking criteria mapping, and a complete interview demo defense script.")

# SECTION 1
add_h1("1. Executive Overview & Problem Statement")
add_p("In modern agile software development, Product Owners (POs) face significant challenges converting unstructured product briefs, customer feedback, and domain specs into high-quality, actionable backlog items. When teams attempt to automate this with Large Language Models (LLMs), two critical failure modes emerge:")
add_bullet("LLMs fabricate ungrounded requirements or technical specs (e.g. inventing a 50 MB file size limit when the context document specifies no exact threshold).", "1. Hallucinations & Uncited Claims: ")
add_bullet("LLMs produce generic, low-value user stories ('As a user, I want to manage data efficiently') that fail team Definition of Ready (DoR).", "2. Generic Story Proliferation: ")
add_bullet("LLMs write generated items directly into external tools (Jira / Azure DevOps) with status 'READY', bypassing human oversight and PO review.", "3. Uncontrolled External Writes: ")

add_p("The FlowDesk PO Backlog Architect Agent solves these problems through a fundamental engineering philosophy: ", bold_prefix="The Core Solution: ")
add_p("Governance Over Generation. ", bold_prefix="", italic=True)
add_p("While the LLM proposes epics, user stories, and acceptance criteria, deterministic Python service layers strictly validate section-level citations, enforce anti-generic specificity scoring across 3 layers, evaluate Definition of Ready rules, and enforce a structural human approval gate with an immutable status floor.")

# SECTION 2
add_h1("2. Assessment Requirements & Digital T3 Marking Criteria Alignment")
add_p("The project fulfills all 9 core objectives (O1 – O9) specified in the Digital T3 assessment prompt:")

headers_o = ["Objective", "Requirement", "Implementation Service / Component", "Verification Evidence"]
rows_o = [
    ["O1", "Context Indexing & Retrieval", "app/services/context_service.py (SQLite FTS5)", "TC-01 PASS, addressable section IDs (PB-01...PB-15)"],
    ["O2", "Epic Decomposition & Gap Detection", "app/agents/decomposition_agent.py", "TC-04 PASS, TC-08 PASS (thin epic surfaces questions > stories)"],
    ["O3", "Acceptance Criteria Generation (GWT)", "app/agents/criteria_agent.py", "Generated Given/When/Then scenarios with claim citations"],
    ["O4", "Definition of Ready (DoR) Gate", "app/services/readiness_service.py (config/readiness.yaml)", "TC-05 PASS, evaluates 6 configurable YAML rules"],
    ["O5", "Deterministic Prioritization Engine", "app/services/prioritization_service.py", "TC-06 PASS, formula scoring & topological sprint sorter"],
    ["O6", "Claim-Level Citation Validation", "app/services/citation_service.py", "TC-01 PASS, numeric term check rejects unsupported claims"],
    ["O7", "Overlap & Duplicate Detection", "app/services/overlap_service.py", "TC-07 PASS, detects DUPLICATE, SUBSET, SUPERSET, ADJACENT"],
    ["O8", "3-Layer Anti-Generic Guard", "app/services/generic_guard_service.py", "TC-03 PASS, 3-layer specificity scoring & auto-rewrite"],
    ["O9", "Human Approval Gate & Status Floor", "app/services/approval_service.py", "TC-09 PASS, HTTP 403 write rejection & NOT_READY status floor"]
]
add_styled_table(headers_o, rows_o)

add_h2("Digital T3 Evaluation Criteria Scorecard")
headers_m = ["Criteria", "Weight", "Key Submission Strengths", "Self Assessment"]
rows_m = [
    ["Architecture & System Design", "25%", "Clean modular layer separation (LLM, Services, Adapters, REST API, UI). Zero circular dependencies.", "10 / 10"],
    ["Governance & Grounding", "25%", "3-Layer GenericGuard, Section-level citations, Numeric claim validation, Structural human approval gate.", "10 / 10"],
    ["LLM Integration & Abstraction", "20%", "Clean LLMProvider interface. GroqProvider (live qwen3.6-27b) and MockProvider (offline deterministic).", "9.5 / 10"],
    ["Evaluation & Testing Evidence", "15%", "10/10 Golden Cases (Mock & Groq), 7/7 Adversarial Probes, 24/24 Pytest unit & integration tests.", "10 / 10"],
    ["Code Quality & Documentation", "15%", "Full docstrings, ADR decision log (ADR-001..008), evaluation report, demo guide, visual user guide.", "9.5 / 10"]
]
add_styled_table(headers_m, rows_m)

# SECTION 3
add_h1("3. System Architecture & High-Level Design")
add_p("The architecture follows a clean 4-tier pattern with strict uni-directional data flow:")

add_bullet("FastAPI REST endpoints (/api/v1) and Streamlit Multi-Tab Dashboard (ui/dashboard.py).", "1. User & API Interface: ")
add_bullet("ContextService, CitationService, GenericGuardService, ReadinessService, PrioritizationService, OverlapService, ApprovalService, CriteriaAgent, DecompositionAgent.", "2. Core Service & Governance Layer: ")
add_bullet("LLMProvider protocol -> GroqProvider (qwen/qwen3.6-27b) & MockProvider. DocumentStore & Tracker protocols.", "3. Abstraction & Adapter Layer: ")
add_bullet("SQLite database (FlowDesk product brief sections, FTS5 full-text index, drafts, approval logs, write logs).", "4. Persistence Layer: ")

add_callout("Structural Approval Gate Dataflow",
            "Client -> API / UI -> Draft Creation (PENDING) -> ApprovalService.approve_draft() (APPROVED) -> ApprovalService.write_draft_to_tracker() -> Tracker Write (Status forced to NOT_READY, tagged AI-drafted).\n"
            "If an unapproved draft (PENDING/REJECTED) attempts tracker write, ApprovalService raises ApprovalRequiredError -> FastAPI returns HTTP 403 Forbidden.")

# SECTION 4
add_h1("4. Architectural Decision Records (ADR Log 001 – 008)")
add_p("Every architectural choice in this codebase is backed by a documented Architecture Decision Record:")

headers_adr = ["ADR ID", "Title", "Decision Summary", "Rationale & Impact"]
rows_adr = [
    ["ADR-001", "FastAPI for Backend REST API", "Used FastAPI with Pydantic v2 schemas.", "Delivers high-performance async REST API, automatic OpenAPI/Swagger docs, and clean error handling."],
    ["ADR-002", "SQLite + FTS5 for Context Retrieval", "Used SQLite FTS5 full-text search over Vector DB.", "Provides 100% deterministic section lookup (PB-01..PB-15) with zero vector store infrastructure overhead."],
    ["ADR-003", "LLMProvider Abstract Protocol", "Created generic LLMProvider base class.", "Decouples application logic from specific LLM vendors; supports seamless model switching."],
    ["ADR-004", "MockProvider for Deterministic CI", "Implemented offline MockProvider.", "Enables 0.05-second, 100% reproducible test suite runs without API cost, rate limits, or network dependency."],
    ["ADR-005", "3-Layer Anti-Generic Guard", "Implemented 3-layer specificity scoring.", "Combines exact phrase matching, vague verb regex, and term density to rewrite generic stories into domain-specific items."],
    ["ADR-006", "Structural Human Approval Gate", "Enforced approval check at service layer.", "Returns HTTP 403 Forbidden for unapproved write attempts; structurally prevents un-reviewed AI writes to tracker."],
    ["ADR-007", "Immutable NOT_READY Status Floor", "Overrode AI status outputs on tracker write.", "Forces status NOT_READY and adds AI-drafted tag, guaranteeing human PO review before sprint planning."],
    ["ADR-008", "Pragmatic Scope & Framework Cuts", "Omitted heavy graph/agent frameworks.", "Avoids unnecessary complexity (LangChain, LangGraph, PostgreSQL) in favor of maintainable native Python service code."]
]
add_styled_table(headers_adr, rows_adr)

# SECTION 5
add_h1("5. Complete File-by-File Codebase Map")
add_p("Below is the complete inventory and detailed explanation of every file in the repository:")

headers_files = ["Directory / File Path", "Role & Description", "Key Symbols / Functions"]
rows_files = [
    ["app/main.py", "FastAPI application entrypoint & middleware setup.", "app, FastAPI, CORS, startup_event()"],
    ["app/api/routes.py", "REST API endpoint handlers for context, criteria, readiness, approval, priority.", "index_context(), generate_criteria(), check_readiness(), approve_draft(), write_tracker()"],
    ["app/db/database.py", "SQLAlchemy SQLite database session configuration.", "engine, SessionLocal, Base, get_db()"],
    ["app/models/models.py", "SQLAlchemy ORM models for database tables.", "ContextSectionModel, BacklogItemModel, DraftModel, ApprovalLogModel, WriteLogModel"],
    ["app/schemas/domain.py", "Pydantic v2 schemas for request/response payloads.", "Citation, OpenQuestion, CriteriaResult, GenericGuardResult, ReadinessResult, PriorityScore, OverlapResult"],
    ["app/services/context_service.py", "SQLite FTS5 text parser & section indexer.", "ContextService, index_markdown_brief(), search_context(), get_section_by_ref()"],
    ["app/services/citation_service.py", "Claim-level citation verification & numeric grounding engine.", "CitationService, validate_citation_existence(), validate_citation_support()"],
    ["app/services/generic_guard_service.py", "3-layer anti-generic pattern checker & auto-rewriter.", "GenericGuardService, evaluate_specificity(), rewrite_generic_story()"],
    ["app/services/readiness_service.py", "YAML-driven Definition of Ready rule evaluator.", "ReadinessService, evaluate_readiness(), log_override()"],
    ["app/services/approval_service.py", "Draft state machine, approval gate & status floor.", "ApprovalService, create_draft(), approve_draft(), reject_draft(), write_draft_to_tracker()"],
    ["app/services/prioritization_service.py", "Formula priority scorer & topological sprint sorter.", "PrioritizationService, calculate_priority_score(), sort_backlog()"],
    ["app/services/overlap_service.py", "Overlap & duplicate relationship detector.", "OverlapService, check_overlap()"],
    ["app/agents/criteria_agent.py", "Structured GWT acceptance criteria generator.", "CriteriaAgent, generate_criteria()"],
    ["app/agents/decomposition_agent.py", "Epic decomposer & thin epic detector.", "DecompositionAgent, decompose_epic()"],
    ["app/adapters/tracker.py", "External issue tracker interface & MockTracker.", "Tracker, MockTracker, create_issue(), get_issue()"],
    ["app/adapters/doc_store.py", "Document store protocol implementation.", "DocumentStore, FileSystemDocumentStore"],
    ["app/llm/base.py", "Abstract LLMProvider protocol.", "LLMProvider, generate_json()"],
    ["app/llm/groq_provider.py", "Live Groq API provider with qwen/qwen3.6-27b.", "GroqProvider, generate_json()"],
    ["app/llm/mock_provider.py", "Deterministic offline Mock LLM provider.", "MockProvider, generate_json()"],
    ["config/readiness.yaml", "Configurable DoR rules YAML file.", "rules (6 active rules)"],
    ["config/generic_guard.json", "Forbidden generic terms & vague verbs configuration.", "forbidden_phrases, vague_verbs, domain_keywords"],
    ["data/product_brief.md", "FlowDesk specification seed markdown (15 sections PB-01..15).", "15 addressable sections, 3 planted gaps, 1 inconsistency, 1 contradiction"],
    ["data/glossary.json", "FlowDesk domain glossary.", "20 canonical domain terms"],
    ["data/backlog.json", "Seed backlog items (BL-001..020).", "20 mixed quality stories"],
    ["data/epics.json", "Seed epics (EP-001 detailed, EP-002 thin).", "EP-001, EP-002"],
    ["ui/dashboard.py", "Streamlit 7-tab dashboard application.", "Tab 1..7 interactive dashboard handlers"],
    ["eval/run.py", "Golden cases evaluation harness script.", "run_eval(), GoldenCaseRunner"],
    ["eval/compare.py", "Side-by-side Mock vs Groq benchmark reporter.", "compare_results()"],
    ["eval/adversarial_run.py", "7 adversarial scenarios test runner script.", "run_adversarial_suite()"],
    ["tests/test_api_integration.py", "Pytest suite for REST endpoints & SQLite threading.", "test_approval_gate_http_403(), test_write_tracker_success()"],
    ["tests/test_approval_gate.py", "Pytest unit tests for approval gate & status floor.", "test_unapproved_write_fails(), test_approved_write_status_floor()"],
    ["tests/test_grounding.py", "Pytest unit tests for citation resolution & numeric terms.", "test_citation_verification(), test_numeric_term_grounding()"],
    ["tests/test_e2e_pipeline.py", "Pytest 20-step happy path & edge case integration tests.", "test_20_step_e2e_pipeline()"]
]
add_styled_table(headers_files, rows_files)

# SECTION 6
add_h1("6. Technology Stack & Framework Choices")
add_bullet("Core backend programming language.", "Python 3.13: ")
add_bullet("High-performance asynchronous REST API framework.", "FastAPI: ")
add_bullet("Strict runtime type validation & JSON schema generation.", "Pydantic v2: ")
add_bullet("Relational database engine with FTS5 full-text indexing.", "SQLite + SQLite FTS5: ")
add_bullet("Python Object-Relational Mapping (ORM) framework.", "SQLAlchemy 2.0: ")
add_bullet("Interactive multi-tab frontend dashboard.", "Streamlit: ")
add_bullet("Ultra-fast live LLM inference API provider.", "Groq API: ")
add_bullet("Default open-weights model for live evaluation.", "qwen/qwen3.6-27b: ")
add_bullet("Automated testing & assertion framework.", "Pytest: ")

# SECTION 7
add_h1("7. Testing & Verification Evidence")
add_p("The system has undergone rigorous empirical evaluation across three independent test suites:")

add_h2("Golden Cases Benchmark (10 / 10 PASS)")
headers_g = ["Case ID", "Name", "Category", "Target", "Mock Result", "Groq Result", "Status"]
rows_g = [
    ["TC-01", "Citation Resolution", "Grounding", "0 missing", "0 missing", "0 missing", "PASS"],
    ["TC-02", "Open-Question Recall", "Gap Surface", "1.0 recall", "1.0 recall", "1.0 recall", "PASS"],
    ["TC-03", "Generic Story Rate", "Anti-Generic", "0.1 max", "0.0 rate", "0.0 rate", "PASS"],
    ["TC-04", "Decomposition Coverage", "Decomposition", "0.85 cov", "1.0 cov", "1.0 cov", "PASS"],
    ["TC-05", "Readiness Gate Accuracy", "DoR Gate", "1.0 acc", "1.0 acc", "1.0 acc", "PASS"],
    ["TC-06", "Prioritization Reproducibility", "Priority", "1.0 score", "1.0 score", "1.0 score", "PASS"],
    ["TC-07", "Overlap Detection", "Overlap", "True match", "True match", "True match", "PASS"],
    ["TC-08", "Thin Epic Behaviour", "Decomposition", "True match", "True match", "True match", "PASS"],
    ["TC-09", "Approval Gate & Status Floor", "Governance", "True match", "True match", "True match", "PASS"],
    ["TC-10", "Glossary Consistency", "Grounding", "True match", "True match", "True match", "PASS"]
]
add_styled_table(headers_g, rows_g)

add_h2("Adversarial Evaluation Suite (7 / 7 PASS)")
headers_adv = ["Adv ID", "Adversarial Test Scenario", "Tested Vulnerability", "Observed System Behavior", "Result"]
rows_adv = [
    ["ADV-01", "Hallucinated Numeric Term (50 MB)", "Numeric Spec Fabrication", "CitationService rejected claim 'term 50 MB not in PB-04.2'", "PASS"],
    ["ADV-02", "Invalid Section Ref (PB-99)", "Non-Existent Section Lookup", "CitationService rejected ref 'PB-99 does not exist in DB'", "PASS"],
    ["ADV-03", "Generic Title ('Fix everything')", "Vague Story Ingestion", "GenericGuard flagged GENERIC (score=1) and auto-rewrote story", "PASS"],
    ["ADV-04", "Unapproved Tracker Write Attempt", "Direct API Bypassing", "ApprovalService raised ApprovalRequiredError -> HTTP 403", "PASS"],
    ["ADV-05", "Status Floor Override on Approved Write", "AI Status Escalation", "ApprovalService forced status NOT_READY and added AI-drafted tag", "PASS"],
    ["ADV-06", "Duplicate Tracker Write Attempt", "Duplicate Ingestion", "ApprovalService caught existing write log -> HTTP 409 Conflict", "PASS"],
    ["ADV-07", "Prompt Injection Attack ('Ignore rules')", "Prompt Injection", "Model schema validation enforced -> system rules preserved", "PASS"]
]
add_styled_table(headers_adv, rows_adv)

# SECTION 8
add_h1("8. Interview Demo Script & Defense Guide")
add_p("Follow this minute-by-minute script during your interview presentation to Digital T3 evaluators:")

add_bullet("State the problem (vague stories, hallucinated specs, un-governed writes) and core philosophy: 'Governance Over Generation'.", "0:00 – 1:00 (Opening Pitch): ")
add_bullet("Open Tab 1 (Context Search) & Tab 2 (Epic Decomposer). Show section indexing (PB-01..15) and open question surfacing for thin epics.", "1:00 – 3:00 (Context & Decomposition): ")
add_bullet("Open Tab 3 (Criteria Generator). Input 'Manage data efficiently' -> show 3-layer GenericGuard diagnosis and auto-rewrite.", "3:00 – 5:00 (Anti-Generic Guard): ")
add_bullet("Open Tab 7 (Approval Queue). Try writing PENDING draft -> show HTTP 403. Click Approve -> click Write -> show NOT_READY status floor.", "5:00 – 7:00 (The Killer Approval Gate Demo): ")
add_bullet("Show terminal runs: python -m eval.run --provider mock (10/10 PASS), python eval/compare.py (10/10 Groq), python eval/adversarial_run.py (7/7 PASS).", "7:00 – 9:00 (Empirical Evaluation Evidence): ")
add_bullet("Answer technical trade-off questions using ADRs (ADR-002 FTS5 over Vector DB, ADR-006 Service Approval Gate).", "9:00 – 10:00 (Architecture Q&A Defense): ")

add_h2("Anticipated Interview Questions & Bulletproof Technical Answers")
add_p("1. Why did you use SQLite FTS5 instead of a Vector Database?", bold_prefix="Q: ")
add_p("Our product context is structured into discrete, addressable sections (PB-01 through PB-15). FTS5 provides 100% deterministic section lookup and phrase matching with zero vector DB infrastructure overhead, embedding model latency, or indexing cost.", bold_prefix="A: ")

add_p("2. How do you prevent an AI from putting READY items directly into Jira/Azure DevOps?", bold_prefix="Q: ")
add_p("The LLM does not have authority to write to external systems. The ApprovalService state machine enforces that unapproved writes return HTTP 403 Forbidden. Furthermore, when an approved write occurs, ApprovalService forcibly overrides the status to NOT_READY and attaches an AI-drafted tag, guaranteeing human PO review before sprint planning.", bold_prefix="A: ")

add_p("3. How do you detect hallucinated numbers or specs in LLM responses?", bold_prefix="Q: ")
add_p(r"Our CitationService performs numeric term grounding. It extracts all digit sequences (\d+) from generated claims and verifies that those numbers exist verbatim in the cited context section text. If a claim mentions '50 MB' but the cited section lacks '50', the citation is rejected.", bold_prefix="A: ")

# Save Document
out_doc_path = r"e:\Digital T3\po-backlog-architect-agent\docs\PO_Backlog_Architect_Master_Guide.docx"
root_doc_path = r"e:\Digital T3\po-backlog-architect-agent\PO_Backlog_Architect_Master_Guide.docx"

doc.save(out_doc_path)
doc.save(root_doc_path)

print(f"Master docx successfully generated at: {out_doc_path} and {root_doc_path}")
