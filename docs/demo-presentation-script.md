# 🎙️ Word-for-Word Demo Presentation Script with Inline Screen & Code Cues

**Project**: FlowDesk PO Backlog Architect Agent  
**Target Duration**: 10 Minutes (600 Seconds)  
**File Artifact**: `PO_Backlog_Architect_Demo_Presentation_Script.docx` (Saved in repository root and `docs/`)

---

## 🛠️ Pre-Demo Setup & Screen Configuration

1. **Terminal 1**: Running FastAPI Backend (`C:\Users\benur\miniconda3\python.exe -m uvicorn app.main:app --reload`)
2. **Terminal 2**: Running Streamlit UI (`C:\Users\benur\miniconda3\python.exe -m streamlit run ui/dashboard.py`)
3. **Screen Layout**:
   - **Left Half of Screen**: Browser window with Streamlit UI ([http://localhost:8501](http://localhost:8501))
   - **Right Half of Screen**: VS Code open with repository files

---

## ⏱️ Minute-by-Minute Spoken Script ("Lyrics") with Inline Visual Cues

### Part 1: 0:00 – 1:30 | Opening Pitch & Architecture Philosophy

> *"Hello everyone! Today I'm presenting the PO Backlog Architect Agent for FlowDesk. **[SHOW UI: Streamlit Sidebar at http://localhost:8501 - LLM Provider Selector & Active Safeguards]** Notice in our Streamlit sidebar that we support two LLM providers via our abstract LLMProvider protocol **[SHOW CODE: app/llm/base.py:L1-L30]**: GroqProvider using open-weights model qwen/qwen3.6-27b for live AI inference **[SHOW CODE: app/llm/groq_provider.py:L1-L85]**, and MockProvider for fast, 0.05-second deterministic offline testing **[SHOW CODE: app/llm/mock_provider.py:L1-L75]**. When engineering teams try using LLMs to generate user stories and acceptance criteria, three major failure modes occur: First, hallucinated technical requirements—like an AI inventing a 50 MB file size limit when the specification has no exact number. Second, generic story proliferation—vague user stories like 'As a user, I want to manage data efficiently' that fail Definition of Ready. And third, uncontrolled external writes—where an LLM pushes unreviewed items directly into Jira or Azure DevOps as READY. Our core design philosophy is GOVERNANCE OVER GENERATION **[SHOW CODE: README.md:L212-L235 (Architecture Component Boundaries Diagram)]**. The LLM proposes artifacts, but deterministic Python service code validates section-level citations, scores anti-generic specificity across 3 layers, evaluates Definition of Ready rules, and enforces a structural human approval gate with an immutable NOT_READY status floor."*

---

### Part 2: 1:30 – 3:00 | Context Indexing (O1) & Epic Decomposition (O2)

> *"First, let's look at Context Indexing in Tab 1 **[SHOW UI: Streamlit Tab 1 - Context Search (O1)]**. We parse the FlowDesk product brief into 15 addressable sections, indexed with SQLite FTS5 **[SHOW CODE: app/services/context_service.py:L15-L65]**. If I search 'file upload' **[ACTION: Type 'file upload' into search box and click 'Search Context']**, the engine retrieves section PB-04.1. This addressable indexing is what enables claim-level citation validation. Now let me move to Tab 2: Epic Decomposition **[SHOW UI: Streamlit Tab 2 - Epic Decomposer (O2)]**. If I select EP-001—a detailed document management epic **[SHOW CODE: data/epics.json:L1-L8 and ACTION: Select 'EP-001' and click 'Decompose Epic']**—the agent generates structured stories with citations **[SHOW CODE: app/agents/decomposition_agent.py:L20-L80]**. However, look at EP-002—a thin, 6-word epic titled 'Automate Approval Overrides' **[SHOW CODE: data/epics.json:L9-L16 and ACTION: Select 'EP-002' and click 'Decompose Epic']**. Instead of fabricating fake requirements, our decomposition agent detects that detail is missing and surfaces Open Questions to the Product Owner first, such as 'What role is authorized to perform overrides?'"*

---

### Part 3: 3:00 – 4:30 | Acceptance Criteria (O3), Citations (O6) & Anti-Generic Guard (O8)

> *"In Tab 3, we generate Given/When/Then acceptance criteria **[SHOW UI: Streamlit Tab 3 - Criteria Generator (O3/O6/O8)]**. When I select story BL-001 **[ACTION: Select story 'BL-001' and click 'Generate Criteria']**, the agent produces testable GWT scenarios and attaches verified citation PB-04.1. Our CitationService **[SHOW CODE: app/services/citation_service.py:L30-L95]** checks both existence and numeric term grounding. Below, we have our 3-Layer Anti-Generic Guard **[SHOW UI: Streamlit Tab 3 Lower Section]**. If someone inputs a vague requirement like 'Manage my data efficiently' **[ACTION: Type 'Manage my data efficiently' in custom text box and click 'Evaluate Specificity']**, our guard evaluates 3 layers: Layer 1 exact phrase match ('manage data'), Layer 2 vague verb regex ('manage') **[SHOW CODE: config/generic_guard.json:L1-L35]**, and Layer 3 specificity score **[SHOW CODE: app/services/generic_guard_service.py:L40-L110]**. It flags the story as GENERIC (Score = 1) and automatically rewrites it into a domain-specific user story with a measurable outcome."*

---

### Part 4: 4:30 – 6:00 | Readiness Gate (O4), Prioritization (O5) & Overlap Detector (O7)

> *"In Tab 4, we evaluate the Definition of Ready **[SHOW UI: Streamlit Tab 4 - Readiness Gate (O4)]**. Selecting BL-003 **[ACTION: Select 'BL-003' and click 'Evaluate Readiness']**—which lacks acceptance criteria—fails rule check 'has_acceptance_criteria' **[SHOW CODE: config/readiness.yaml:L1-L32 and app/services/readiness_service.py:L25-L75]** and returns status BLOCKED. Selecting BL-005 **[ACTION: Select 'BL-005' and click 'Evaluate Readiness']** passes all 6 YAML rules and returns status READY. In Tab 5 **[SHOW UI: Streamlit Tab 5 - Prioritization Engine (O5)]**, our Prioritization Engine **[SHOW CODE: app/services/prioritization_service.py:L30-L80]** calculates scores using a transparent mathematical formula combining Business Value, Urgency, Risk Reduction, Dependency Penalty, and Readiness Factor **[ACTION: Click 'Run Prioritization Engine']**. We don't ask the LLM for priority; we compute it deterministically. In Tab 6 **[SHOW UI: Streamlit Tab 6 - Overlap Detector (O7)]**, Overlap Detector **[SHOW CODE: app/services/overlap_service.py:L20-L70]** checks new candidate story BL-006 **[ACTION: Select 'BL-006' and click 'Check Overlap']** against existing backlog stories and identifies it as a SUBSET of story BL-001 with 92% confidence, recommending a merge."*

---

### Part 5: 6:00 – 7:30 | ⭐ The Killer Demo: Human Approval Gate & Status Floor (O9)

> *"Now for our core safety control in Tab 7: The Human Approval Gate and Status Floor **[SHOW UI: Streamlit Tab 7 - Approval Queue (O9)]**. Notice draft DFT-001 in the queue with status PENDING. If an external system or user attempts to write this unapproved draft directly to MockTracker, watch what happens when I click 'Write to Tracker' **[ACTION 1: Click 'Write to Tracker' on PENDING draft]**: The service layer rejects the call and returns HTTP 403 Forbidden: Draft must be APPROVED **[SHOW CODE: app/services/approval_service.py:L72 (if draft.status != ApprovalStatus.APPROVED: raise ApprovalRequiredError)]**. Now, as the human Product Owner, I click 'Approve Draft' **[ACTION 2: Click 'Approve Draft']**. The status changes to APPROVED. Now I click 'Write to Tracker' again **[ACTION 3: Click 'Write to Tracker']**. The call succeeds with HTTP 200 OK. But look at MockTracker **[SHOW CODE: app/services/approval_service.py:L90-L115 (write_draft_to_tracker forcing status=NOT_READY)]**: Even though the draft was approved, the status is forcibly locked at NOT_READY and tagged 'AI-drafted'. This guarantees that no AI item enters a sprint without final human PO review."*

---

### Part 6: 7:30 – 9:00 | Empirical Evaluation Harness & Adversarial Proofs

> *"To prove our system is robust beyond UI demonstrations, we built an automated evaluation suite **[SHOW UI: Switch focus to Terminal window]**. In Terminal, I run 'python -m eval.run --provider mock' **[ACTION: Run 'python -m eval.run --provider mock' in Terminal and SHOW CODE: eval/run.py:L20-L100]**—achieving 10/10 PASS across all Golden Cases in 0.05 seconds. Next, running 'python eval/compare.py' **[ACTION: Run 'python eval/compare.py' in Terminal and SHOW CODE: eval/compare.py:L10-L60]** benchmarks our deterministic Mock against live Groq LLM inference with qwen/qwen3.6-27b over 3 repeated runs. Groq achieves 10/10 PASS with 1.45-second average latency, zero retries, and zero schema failures. Finally, running 'python eval/adversarial_run.py' **[ACTION: Run 'python eval/adversarial_run.py' in Terminal and SHOW CODE: eval/adversarial_run.py:L15-L90]** executes 7 adversarial probes—achieving 7/7 PASS. For example, ADV-01 injects a hallucinated '50 MB' file limit. CitationService detects that '50 MB' is not in PB-04.2 and rejects the claim."*

---

### Part 7: 9:00 – 10:00 | Architectural Trade-offs & Q&A Defense Strategy

> *"In conclusion, our project evolved from a feature prototype into a governed AI Product Owner system. We made three key architectural decisions documented in our ADR log **[SHOW CODE: docs/decision-log.md:L1-L150]**: First, we chose SQLite FTS5 over Vector DBs **[SHOW CODE: docs/decision-log.md - ADR-002]** because our product brief is structured into addressable sections (PB-01 to PB-15). FTS5 provides 100% deterministic lookup with zero vector infrastructure overhead. Second, we built MockProvider alongside GroqProvider **[SHOW CODE: docs/decision-log.md - ADR-004]** to enable fast, reproducible CI regression testing. And third, we enforced approval gating and status floors in Python service objects **[SHOW CODE: docs/decision-log.md - ADR-006 & ADR-008]** rather than complex graph frameworks, keeping the codebase clean, maintainable, and robust. Thank you! I am now ready for any technical questions."*
