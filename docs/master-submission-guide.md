# 📘 PO Backlog Architect Agent — Master System Guide & UI Operations Manual

**Project**: FlowDesk PO Backlog Architect Agent  
**Format**: Master Reference Guide, Step Dependency Map, UI Handbook & Study Document  
**File Artifact**: `PO_Backlog_Architect_Master_Guide.docx` (Available in repository root and `docs/`)

---

## 1. Why Have a UI? The Strategic Purpose of the Application

If the core backend is built in Python and FastAPI, why do we need a Streamlit UI dashboard?

The Streamlit UI serves three fundamental strategic purposes:

1. **Human-in-the-Loop Governance**: AI models are probabilistic and will occasionally output incomplete, vague, or misaligned user stories. A pure automated script would push AI drafts straight to production trackers. The UI provides an interactive dashboard where a human Product Owner (PO) can inspect context citations, review surfaced open questions, trigger anti-generic checks, evaluate Definition of Ready (DoR), and explicitly approve drafts.
2. **Interactive Interview Demo Environment**: In an assessment or interview demo, evaluators (like Digital T3 engineers) will not want to curl raw REST endpoints or read Python terminal logs. The Streamlit UI provides a visual, multi-tab interface where anyone can verify the agent's capabilities in real-time with zero technical setup.
3. **Visual Evidence of System Safeguards**: The UI exposes system safeguards clearly in the sidebar (`Auto-Fail Safeguards Active: Structural Approval Gate, Status Floor, Citation Verification`). This proves that governance is enforced at the service layer, not just in UI code.

---

## 2. System Lifecycle & Step Dependency Map (How Steps Connect)

The 7 modules in the UI form a logical, sequential workflow pipeline. Understanding how data flows between steps is essential for explaining the system during your demo:

| Step / Tab | Name | Prerequisite Dependencies (What It Uses) | Output Produced (What It Feeds Into Next) |
|------------|------|------------------------------------------|-------------------------------------------|
| **Step 1** | **Context Search (O1)** | FlowDesk Product Brief (`data/product_brief.md`) | Provides addressable section IDs (`PB-01` … `PB-15`) for Step 2 & Step 3 grounding. |
| **Step 2** | **Epic Decomposer (O2)** | Step 1 Context Sections + Seed Epics (`EP-001`/`002`) | Decomposes epics into User Stories & Open Questions. Generated stories feed into Step 3, 4, 5 & 7. |
| **Step 3** | **Criteria Generator (O3/O6/O8)** | User Story from Step 2 + Step 1 Addressable Context | Generates Given/When/Then criteria + Citations. Feeds into Step 4 (DoR check) & Step 7 (Draft Queue). Runs 3-Layer GenericGuard. |
| **Step 4** | **Readiness Gate (O4)** | Story + Acceptance Criteria (Step 3) + `config/readiness.yaml` | Evaluates 6 DoR rules. Outputs status `READY` or `BLOCKED`. Status feeds into Step 5 & Step 7. |
| **Step 5** | **Prioritization Engine (O5)** | Backlog Items + DoR Status (Step 4) + Dependency Rules | Calculates weighted formula score. Sorts backlog topologically for sprint planning. |
| **Step 6** | **Overlap Detector (O7)** | New Candidate Story (Step 2/3) + Existing Backlog (`BL-001`..`020`) | Detects `DUPLICATE`, `SUBSET`, `SUPERSET`, `ADJACENT` relationships to prevent duplicate work. |
| **Step 7** | **Approval Queue & Write Gate (O9)** | Drafts generated in Step 2/3 + DoR status from Step 4 | Enforces Human PO Approval (`PENDING` → `APPROVED`). Rejects unapproved writes (`HTTP 403`). Forces status floor `NOT_READY` and tag `AI-drafted`. |

### The End-to-End Dependency Chain Example:
1. **Step 1** indexes section `PB-04.1` (*"Document Upload Format"*).
2. **Step 2** uses `PB-04.1` to generate User Story `BL-001` (*"Upload document attachment"*).
3. **Step 3** generates GWT Acceptance Criteria and attaches citation `PB-04.1` to story `BL-001`.
4. **Step 4** checks story `BL-001`: since it has criteria and citations, DoR returns status `READY`.
5. **Step 5** scores story `BL-001` (Priority Score = 8.45) and places it at the top of Sprint 1.
6. **Step 7** receives story `BL-001` as Draft `DFT-001` (`PENDING`). PO clicks Approve, then Write to Tracker. `ApprovalService` writes issue to `MockTracker` with status `NOT_READY` and tag `AI-drafted`.

---

## 3. Granular UI Operations Guide (Exact Inputs & Button Clicks for All Steps)

### Step 1: Context Indexing & Addressable Search (Tab 1)
- **UI Elements**: FTS5 full-text search bar and section lookup cards.
- **What to Input**: Type a search term into the input box: e.g., `file upload`, `approval`, `requester`, or `file size`.
- **What to Click**: Click the **"Search Context"** button.
- **Expected Outcome**: Displays `Found N Addressable Sections`. Expand `[PB-04] Document & File Upload Management` to see verbatim section text indexed with section ID `PB-04.1`.
- **Demo Talking Point**: *"Notice how every section of our product brief has a unique ID (PB-01 to PB-15). This addressable index allows our agents to validate claims against exact citations."*

---

### Step 2: Epic Decomposer & Gap Detection (Tab 2)
- **UI Elements**: Epic selector dropdown, **"Decompose Epic"** button.
- **What to Input**: Select `EP-001 Document Management` (Detailed Epic) OR `EP-002 Approval Automation` (Thin Epic).
- **What to Click**: Click the **"Decompose Epic"** button.
- **Expected Outcome**:
  - For `EP-001`: Displays decomposed user stories with role, action, benefit, and citations.
  - For `EP-002` (Thin Epic): The system detects insufficient detail and surfaces **Open Questions > Stories** (e.g. *"Undefined approver role"*).
- **Demo Talking Point**: *"When an epic lacks detail like EP-002, our decomposer doesn't fabricate stories; it surfaces open questions to the PO first."*

---

### Step 3: Acceptance Criteria & Anti-Generic Guard (Tab 3)
- **UI Elements**: Story selector, **"Generate Criteria"** button, Anti-Generic Guard custom text input, **"Evaluate Specificity"** button.
- **What to Input**:
  - **Part A**: Select story `BL-001`.
  - **Part B (Generic Check)**: Type `"Manage my data efficiently"` into the custom text box.
- **What to Click**: Click **"Generate Criteria"** for Part A, or **"Evaluate Specificity"** for Part B.
- **Expected Outcome**:
  - **Part A**: Outputs Given/When/Then scenarios with verified citation `PB-04.1`.
  - **Part B**: 3-Layer GenericGuard flags the text as `GENERIC` (`Score = 1`, phrase match *"manage data"*, vague verb *"manage"*) and presents an auto-rewritten story.
- **Demo Talking Point**: *"Our GenericGuard uses 3 detection layers—exact phrases, vague verbs, and term density—to stop vague requirements from entering the sprint."*

---

### Step 4: Definition of Ready (DoR) Gate (Tab 4)
- **UI Elements**: Backlog item selector, **"Evaluate Readiness"** button.
- **What to Input**: Select story `BL-003` (Incomplete story lacking acceptance criteria) OR `BL-005` (Complete story).
- **What to Click**: Click **"Evaluate Readiness"**.
- **Expected Outcome**:
  - For `BL-003`: Evaluates 6 rules from `config/readiness.yaml`. Shows `has_acceptance_criteria = FAIL`. Final Status: `BLOCKED`.
  - For `BL-005`: All 6 rules PASS. Final Status: `READY`.
- **Demo Talking Point**: *"The readiness engine strictly evaluates YAML rules. Incomplete items like BL-003 are BLOCKED until criteria and citations are attached."*

---

### Step 5: Prioritization Engine (Tab 5)
- **UI Elements**: **"Run Prioritization Engine"** button, scored backlog table, formula breakdown cards.
- **What to Input**: No text input needed; uses backlog items from SQLite database.
- **What to Click**: Click **"Run Prioritization Engine"**.
- **Expected Outcome**: Renders a table sorted by Priority Score. Expanding an item shows the explicit mathematical formula:
  $$\text{Score} = (BV \times 0.3) + (Urg \times 0.2) + (RR \times 0.2) + (SA \times 0.15) - (DP \times 0.1) + (RF \times 0.05)$$
- **Demo Talking Point**: *"Prioritization is 100% deterministic and transparent. We don't ask the LLM for a priority number; we compute it from an explicit formula."*

---

### Step 6: Overlap & Duplicate Detector (Tab 6)
- **UI Elements**: Candidate story selector, **"Check Overlap"** button.
- **What to Input**: Select candidate story `BL-006` (Document Upload Request).
- **What to Click**: Click **"Check Overlap"**.
- **Expected Outcome**: Outputs relationship classification: `SUBSET` / `DUPLICATE` with target item `BL-001` (`Confidence = 0.92`) and recommends merging items.
- **Demo Talking Point**: *"Overlap detection prevents duplicate engineering effort by analyzing story semantics against existing backlog items."*

---

### Step 7: Approval Queue & Write Gate (Tab 7 - The Killer Demo)
- **UI Elements**: Draft queue table, **"Approve Draft"**, **"Reject Draft"**, and **"Write to Tracker"** buttons.
- **What to Input**: Select draft `DFT-001` (Status: `PENDING`).
- **What to Click**:
  - **FIRST**: Click **"Write to Tracker"** while status is `PENDING`.
  - **SECOND**: Click **"Approve Draft"**.
  - **THIRD**: Click **"Write to Tracker"** again.
- **Expected Outcome**:
  - **FIRST CLICK**: Error banner appears: **`HTTP 403 Forbidden: Draft DFT-001 must be APPROVED before writing to tracker`**.
  - **SECOND CLICK**: Draft status changes to `APPROVED`.
  - **THIRD CLICK**: Returns `HTTP 200 OK`. `MockTracker` displays item with status forced to **`NOT_READY`** and tagged **`AI-drafted`**.
- **Demo Talking Point**: *"This is our core safety control. Unapproved AI writes return HTTP 403 Forbidden. Even when approved, the status floor forces NOT_READY and tags AI-drafted, guaranteeing human PO review."*

---

## 4. Assessment Requirements & Digital T3 Marking Criteria Alignment

| Objective | Requirement | Implementation Component | Verification Evidence |
|-----------|-------------|--------------------------|-----------------------|
| **O1** | Context Indexing & Retrieval | `app/services/context_service.py` (SQLite FTS5) | TC-01 PASS, addressable section IDs (`PB-01`…`PB-15`) |
| **O2** | Epic Decomposition & Gap Detection | `app/agents/decomposition_agent.py` | TC-04 PASS, TC-08 PASS (thin epic surfaces questions > stories) |
| **O3** | Acceptance Criteria Generation (GWT) | `app/agents/criteria_agent.py` | Generated Given/When/Then scenarios with citations |
| **O4** | Definition of Ready (DoR) Gate | `app/services/readiness_service.py` (`config/readiness.yaml`) | TC-05 PASS, evaluates 6 configurable YAML rules |
| **O5** | Deterministic Prioritization Engine | `app/services/prioritization_service.py` | TC-06 PASS, formula scoring & topological sprint sorter |
| **O6** | Claim-Level Citation Validation | `app/services/citation_service.py` | TC-01 PASS, numeric term check rejects unsupported claims |
| **O7** | Overlap & Duplicate Detection | `app/services/overlap_service.py` | TC-07 PASS, detects `DUPLICATE`, `SUBSET`, `SUPERSET`, `ADJACENT` |
| **O8** | 3-Layer Anti-Generic Guard | `app/services/generic_guard_service.py` | TC-03 PASS, 3-layer specificity scoring & auto-rewrite |
| **O9** | Human Approval Gate & Status Floor | `app/services/approval_service.py` | TC-09 PASS, HTTP 403 write rejection & `NOT_READY` status floor |

---

## 5. Architectural Decision Records (ADR Log 001 – 008)

1. **ADR-001 (FastAPI Backend)**: Used FastAPI with Pydantic v2 schemas for high performance and OpenAPI documentation.
2. **ADR-002 (SQLite FTS5 Context Indexing)**: Replaced vector database complexity with 100% deterministic section lookup (`PB-01` … `PB-15`).
3. **ADR-003 (LLMProvider Abstract Protocol)**: Created a Python `LLMProvider` protocol interface to decouple domain logic from specific LLM vendors.
4. **ADR-004 (MockProvider for Deterministic CI)**: Implemented an offline `MockProvider` returning deterministic JSON for 0.05-second test suite runs.
5. **ADR-005 (3-Layer Anti-Generic Guard)**: Implemented 3-layer specificity scoring (exact phrase match, vague verb regex, term density) to auto-rewrite generic user stories.
6. **ADR-006 (Structural Human Approval Gate)**: Enforced draft approval check at the service layer, returning `HTTP 403 Forbidden` if an unapproved draft tries to write to the tracker.
7. **ADR-007 (Immutable NOT_READY Status Floor)**: Overrode LLM status output on external tracker write, locking status to `NOT_READY` and attaching tag `AI-drafted`.
8. **ADR-008 (Pragmatic Scope & Framework Boundaries)**: Omitted heavy agent frameworks (LangChain, LangGraph, PostgreSQL) in favor of maintainable native Python service code.

---

## 6. Testing & Evidence Results

### Golden Cases Benchmark (10 / 10 PASS)
Both `MockProvider` and `GroqProvider` (`qwen/qwen3.6-27b`) achieved **100.0% pass rate** across all 10 Golden Cases. Average Groq latency: **1.45s**. Zero retries, zero schema failures.

### Adversarial Suite (7 / 7 PASS)
1. **ADV-01 (Hallucinated 50 MB term)**: Rejected by `CitationService` (*"numeric term 50 MB not found in context"*).
2. **ADV-02 (Invalid section ref PB-99)**: Rejected by `CitationService` (*"section PB-99 does not exist in DB"*).
3. **ADV-03 (Generic title 'Fix everything')**: Flagged by `GenericGuard` (`GENERIC`, score=1) and auto-rewritten.
4. **ADV-04 (Unapproved tracker write attempt)**: Rejected with `HTTP 403 Forbidden`.
5. **ADV-05 (Status floor override on approved write)**: Status forced to `NOT_READY` and tagged `AI-drafted`.
6. **ADV-06 (Duplicate tracker write attempt)**: Intercepted with `HTTP 409 Conflict`.
7. **ADV-07 (Prompt injection attack 'Ignore rules')**: Schema validation preserved system instructions.

---

## 7. Interview Q&A Defense Script

- **Q1: Why did you use SQLite FTS5 instead of a Vector Database?**  
  *A: Our product context is structured into discrete, addressable sections (PB-01 through PB-15). FTS5 provides 100% deterministic section lookup and phrase matching with zero vector DB infrastructure overhead, embedding model latency, or indexing cost.*

- **Q2: How do you prevent an AI from putting READY items directly into Jira/Azure DevOps?**  
  *A: The LLM does not have authority to write to external systems. The ApprovalService state machine enforces that unapproved writes return HTTP 403 Forbidden. Furthermore, when an approved write occurs, ApprovalService forcibly overrides the status to NOT_READY and attaches an AI-drafted tag, guaranteeing human PO review before sprint planning.*

- **Q3: How do you detect hallucinated numbers or specs in LLM responses?**  
  *A: Our CitationService performs numeric term grounding. It extracts all digit sequences (\d+) from generated claims and verifies that those numbers exist verbatim in the cited context section text. If a claim mentions '50 MB' but the cited section lacks '50', the citation is rejected.*
