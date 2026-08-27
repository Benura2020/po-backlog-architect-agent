# 🎙️ Word-for-Word Demo Presentation Script & Visual Walkthrough

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

## ⏱️ Minute-by-Minute Script & Visual Actions

### Part 1: 0:00 – 1:30 | Opening Pitch & Architecture Philosophy
* **Screen Action**: Streamlit UI Homepage ([http://localhost:8501](http://localhost:8501)). Point out sidebar dropdown: toggle between `Groq (qwen/qwen3.6-27b)` and `Mock (Deterministic)`. Then switch to VS Code [`README.md:L212-L235`](README.md#L212-L235).
* **Code Reference**:
  - `README.md:L212-L235` (Architecture Component Boundaries Diagram)
  - `app/llm/base.py:L1-L30` (`LLMProvider` abstract protocol)
  - `app/llm/groq_provider.py:L1-L85` (`GroqProvider` using `qwen/qwen3.6-27b`)
  - `app/llm/mock_provider.py:L1-L75` (`MockProvider` deterministic mock)
* **Word-for-Word Spoken Script**:
  > *"Hello everyone! Today I'm presenting the PO Backlog Architect Agent for FlowDesk. Notice in our Streamlit sidebar that we support two LLM providers via our abstract LLMProvider protocol: GroqProvider using open-weights model qwen/qwen3.6-27b for live AI inference, and MockProvider for fast, 0.05-second deterministic offline testing. When engineering teams try using LLMs to generate user stories and acceptance criteria, three major failure modes occur: First, hallucinated technical requirements—like an AI inventing a 50 MB file size limit when the specification has no exact number. Second, generic story proliferation—vague user stories like 'As a user, I want to manage data efficiently' that fail Definition of Ready. And third, uncontrolled external writes—where an LLM pushes unreviewed items directly into Jira or Azure DevOps as READY. Our core design philosophy is GOVERNANCE OVER GENERATION. The LLM proposes artifacts, but deterministic Python service code validates section-level citations, scores anti-generic specificity across 3 layers, evaluates Definition of Ready rules, and enforces a structural human approval gate with an immutable NOT_READY status floor."*

---

### Part 2: 1:30 – 3:00 | Context Indexing (O1) & Epic Decomposition (O2)
* **Screen Action**:
  1. Streamlit Tab 1: Search `file upload`, show section `[PB-04.1]`.
  2. Streamlit Tab 2: Decompose `EP-001` (detailed), then `EP-002` (thin epic - 6 words). Show open questions surfaced instead of fabricated stories.
* **Code Reference**:
  - `app/services/context_service.py:L15-L65` (`index_markdown_brief`)
  - `data/epics.json:L1-L17` (`EP-001` vs `EP-002`)
  - `app/agents/decomposition_agent.py:L20-L80` (`decompose_epic`)
* **Word-for-Word Spoken Script**:
  > *"First, let's look at Context Indexing in Tab 1. We parse the FlowDesk product brief into 15 addressable sections, indexed with SQLite FTS5. If I search 'file upload', the engine retrieves section PB-04.1. This addressable indexing is what enables claim-level citation validation. Now let's move to Tab 2: Epic Decomposition. If I select EP-001—a detailed document management epic—the agent generates structured stories with citations. However, look at EP-002—a thin, 6-word epic titled 'Automate Approval Overrides'. Instead of fabricating fake requirements, our decomposition agent detects that detail is missing and surfaces Open Questions to the Product Owner first, such as 'What role is authorized to perform overrides?'"*

---

### Part 3: 3:00 – 4:30 | Acceptance Criteria (O3), Citations (O6) & Anti-Generic Guard (O8)
* **Screen Action**:
  1. Streamlit Tab 3: Select `BL-001`, click **Generate Criteria**. Show GWT + citation `PB-04.1`.
  2. Streamlit Tab 3 (Lower Section): Input `"Manage my data efficiently"`, click **Evaluate Specificity**. Show 3-layer diagnostic (`GENERIC`, score=1) and auto-rewritten story.
* **Code Reference**:
  - `app/services/citation_service.py:L30-L95` (`validate_citation_support` & numeric term check)
  - `config/generic_guard.json:L1-L35` (`forbidden_phrases` & `vague_verbs`)
  - `app/services/generic_guard_service.py:L40-L110` (`evaluate_specificity` & rewrite)
* **Word-for-Word Spoken Script**:
  > *"In Tab 3, we generate Given/When/Then acceptance criteria. When I select story BL-001, the agent produces testable GWT scenarios and attaches verified citation PB-04.1. Our CitationService checks both existence and numeric term grounding. Below, we have our 3-Layer Anti-Generic Guard. If someone inputs a vague requirement like 'Manage my data efficiently', our guard evaluates 3 layers: Layer 1 exact phrase match ('manage data'), Layer 2 vague verb regex ('manage'), and Layer 3 specificity score. It flags the story as GENERIC (Score = 1) and automatically rewrites it into a domain-specific user story with a measurable outcome."*

---

### Part 4: 4:30 – 6:00 | Readiness Gate (O4), Prioritization (O5) & Overlap Detector (O7)
* **Screen Action**:
  1. Streamlit Tab 4: Select `BL-003` (`BLOCKED`), then `BL-005` (`READY`).
  2. Streamlit Tab 5: Click **Run Prioritization Engine**. Show priority table & formula card: $\text{Score} = (BV \times 0.3) + (Urg \times 0.2) + ...$.
  3. Streamlit Tab 6: Select `BL-006`, click **Check Overlap**. Show `SUBSET`/`DUPLICATE` relation with `BL-001`.
* **Code Reference**:
  - `config/readiness.yaml:L1-L32` (6 active DoR rules)
  - `app/services/readiness_service.py:L25-L75` (`evaluate_readiness`)
  - `app/services/prioritization_service.py:L30-L80` (`calculate_priority_score` formula)
  - `app/services/overlap_service.py:L20-L70` (`check_overlap`)
* **Word-for-Word Spoken Script**:
  > *"In Tab 4, we evaluate the Definition of Ready. Selecting BL-003—which lacks acceptance criteria—fails rule check 'has_acceptance_criteria' and returns status BLOCKED. Selecting BL-005 passes all 6 YAML rules and returns status READY. In Tab 5, our Prioritization Engine calculates scores using a transparent mathematical formula combining Business Value, Urgency, Risk Reduction, Dependency Penalty, and Readiness Factor. We don't ask the LLM for priority; we compute it deterministically. In Tab 6, Overlap Detector checks new candidate story BL-006 against existing backlog stories and identifies it as a SUBSET of story BL-001 with 92% confidence, recommending a merge."*

---

### Part 5: 6:00 – 7:30 | ⭐ The Killer Demo: Human Approval Gate & Status Floor (O9)
* **Screen Action**:
  1. Streamlit Tab 7: Select draft `DFT-001` (Status: `PENDING`).
  2. **FIRST CLICK**: Click **Write to Tracker** -> Error banner **`HTTP 403 Forbidden`**. Show VS Code [`app/services/approval_service.py:L72`](app/services/approval_service.py#L72).
  3. **SECOND CLICK**: Click **Approve Draft** -> Status changes to `APPROVED`.
  4. **THIRD CLICK**: Click **Write to Tracker** -> Success `HTTP 200 OK`. Show MockTracker: status forced to `NOT_READY` and tag `AI-drafted`.
* **Code Reference**:
  - `app/services/approval_service.py:L65-L85` (Line 72: `if draft.status != ApprovalStatus.APPROVED: raise ApprovalRequiredError`)
  - `app/services/approval_service.py:L90-L115` (`write_draft_to_tracker`: forces `status=NOT_READY`, `tags=['AI-drafted']`)
* **Word-for-Word Spoken Script**:
  > *"Now for our core safety control in Tab 7: The Human Approval Gate and Status Floor. Notice draft DFT-001 in the queue with status PENDING. If an external system or user attempts to write this unapproved draft directly to MockTracker, watch what happens when I click 'Write to Tracker': The service layer rejects the call and returns HTTP 403 Forbidden: Draft must be APPROVED. Now, as the human Product Owner, I click 'Approve Draft'. The status changes to APPROVED. Now I click 'Write to Tracker' again. The call succeeds with HTTP 200 OK. But look at MockTracker: Even though the draft was approved, the status is forcibly locked at NOT_READY and tagged 'AI-drafted'. This guarantees that no AI item enters a sprint without final human PO review."*

---

### Part 6: 7:30 – 9:00 | Empirical Evaluation Harness & Adversarial Proofs
* **Screen Action**: Switch to Terminal window.
  1. Run `python -m eval.run --provider mock` -> Show `10 / 10 PASS (100%)`.
  2. Run `python eval/compare.py` -> Show Mock 10/10 vs Groq 10/10 side-by-side report (`1.45s` avg latency).
  3. Run `python eval/adversarial_run.py` -> Show `7 / 7 PASS (100%)` (Highlighting ADV-01 numeric grounding rejection).
* **Code Reference**:
  - `eval/run.py:L20-L100` (`run_eval` & provider CLI)
  - `eval/compare.py:L10-L60` (`compare_results`)
  - `eval/adversarial_run.py:L15-L90` (`run_adversarial_suite`)
* **Word-for-Word Spoken Script**:
  > *"To prove our system is robust beyond UI demonstrations, we built an automated evaluation suite. In Terminal, I run 'python -m eval.run --provider mock'—achieving 10/10 PASS across all Golden Cases in 0.05 seconds. Next, running 'python eval/compare.py' benchmarks our deterministic Mock against live Groq LLM inference with qwen/qwen3.6-27b over 3 repeated runs. Groq achieves 10/10 PASS with 1.45-second average latency, zero retries, and zero schema failures. Finally, running 'python eval/adversarial_run.py' executes 7 adversarial probes—achieving 7/7 PASS. For example, ADV-01 injects a hallucinated '50 MB' file limit. CitationService detects that '50 MB' is not in PB-04.2 and rejects the claim."*

---

### Part 7: 9:00 – 10:00 | Architectural Trade-offs & Q&A Defense Strategy
* **Screen Action**: Switch VS Code window to [`docs/decision-log.md`](docs/decision-log.md) (ADR-002, ADR-004, ADR-006, ADR-008).
* **Code Reference**: `docs/decision-log.md:L1-L150` (ADR-001 through ADR-008)
* **Word-for-Word Spoken Script**:
  > *"In conclusion, our project evolved from a feature prototype into a governed AI Product Owner system. We made three key architectural decisions documented in our ADR log: First, we chose SQLite FTS5 over Vector DBs because our product brief is structured into addressable sections (PB-01 to PB-15). FTS5 provides 100% deterministic lookup with zero vector infrastructure overhead. Second, we built MockProvider alongside GroqProvider to enable fast, reproducible CI regression testing. And third, we enforced approval gating and status floors in Python service objects rather than complex graph frameworks, keeping the codebase clean, maintainable, and robust. Thank you! I am now ready for any technical questions."*
