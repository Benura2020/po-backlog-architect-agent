# Architecture Specification — PO Backlog Architect Agent

## System Overview
The PO Backlog Architect Agent is built with clear architectural boundaries separating persistent seed datasets, full-text context indexing, core LLM agents, deterministic governance algorithms, adapter layers, human approval gating, REST endpoints, Streamlit dashboard UI, and evaluation infrastructure.

---

## 📐 End-to-End Architecture Diagram

```mermaid
flowchart TD
    subgraph DATA["1. Seed Data & Configuration (data/, config/)"]
        PB["product_brief.md (PB-01...PB-15)"]
        GL["glossary.json (20 terms)"]
        BL["backlog.json (20 items)"]
        EP["epics.json (EP-001, EP-002)"]
        CONF_DOR["config/readiness.yaml"]
        CONF_GUARD["config/generic_guard.json"]
    end

    subgraph LLM_LAYER["2. LLM Provider Layer (app/llm/)"]
        LLM_BASE["LLMProvider (Protocol)"]
        GROQ["GroqProvider (qwen/qwen3.6-27b)"]
        MOCK_LLM["MockProvider (Offline Deterministic)"]
        LLM_BASE --> GROQ
        LLM_BASE --> MOCK_LLM
    end

    subgraph DB_LAYER["3. Persistence & Indexing (app/db/, app/services/)"]
        SQLITE[("SQLite DB (flowdesk.db)")]
        FTS5["SQLite FTS5 Indexer (ContextService)"]
        PB --> FTS5
        FTS5 --> SQLITE
    end

    subgraph AGENTS["4. Core Agent Engine (app/agents/, app/services/)"]
        CIT["CitationService (O6 Grounding Verification)"]
        CRIT["CriteriaAgent (O3 GWT Generator & Planted Gap Probe)"]
        DECOMP["DecompositionAgent (O2 Epic Split & Thin Epic Handler)"]
        GUARD["GenericGuardService (O8 Anti-Generic Pattern Filter)"]

        FTS5 --> CIT
        CIT --> CRIT
        FTS5 --> DECOMP
        LLM_LAYER --> CRIT
        LLM_LAYER --> DECOMP
        GUARD --> DECOMP
    end

    subgraph GOVERNANCE["5. Governance & Gating Engine (app/services/)"]
        DOR["ReadinessService (O4 DoR Gate & Human Override Log)"]
        PRIO["PrioritizationService (O5 Deterministic Formula Arithmetic)"]
        OVERLAP["OverlapService (O7 Overlap Relationship Detector)"]
        APPROVAL["ApprovalService (O9 Structural Gate & Status Floor)"]

        CONF_DOR --> DOR
        AGENTS --> DOR
        AGENTS --> OVERLAP
        DOR --> PRIO
    end

    subgraph ADAPTERS["6. External System Adapters (app/adapters/)"]
        TRACKER_PROTO["Tracker (Protocol)"]
        MOCK_TRACKER["MockTracker (Audit Logged)"]
        TRACKER_PROTO --> MOCK_TRACKER
        
        APPROVAL -- "Requires Human Approval\nForces status=NOT_READY" --> MOCK_TRACKER
    end

    subgraph INTERFACE["7. User & API Interface (app/main.py, ui/app.py)"]
        FASTAPI["FastAPI Backend (/api/v1)"]
        STREAMLIT["Streamlit Dashboard (ui/app.py)"]
        EVAL_HARNESS["Eval Harness (eval/run.py - 10 Golden Cases)"]

        GOVERNANCE --> FASTAPI
        FASTAPI --> STREAMLIT
        EVAL_HARNESS --> AGENTS
        EVAL_HARNESS --> GOVERNANCE
    end
```

---

## 🔄 End-to-End Execution Sequence Flow

The diagram below illustrates the exact step-by-step sequence when an Epic or Story is processed from raw intake through human gating to tracker creation:

```mermaid
sequenceDiagram
    autonumber
    actor PO as Human Product Owner
    participant UI as Streamlit UI / FastAPI
    participant CS as ContextService (FTS5)
    participant Agent as CriteriaAgent / DecompositionAgent
    participant Guard as GenericGuardService (app/services/generic_guard_service.py)
    participant DoR as ReadinessService
    participant Gate as ApprovalService
    participant DB as SQLite DB
    participant Tracker as MockTracker Adapter

    PO->>UI: Input Story / Select Epic (e.g. BL-006)
    UI->>CS: Query addressable context (PB-04.1, PB-04.2)
    CS-->>UI: Return section text & stable refs

    UI->>Agent: Generate Criteria / Decompose Epic
    Agent->>CS: Verify citation existence & text support (O6)
    Agent->>Agent: Surface open questions for planted gaps (O3)
    Agent-->>UI: Return structured Pydantic payload

    UI->>Guard: Evaluate Anti-Generic Guard (O8)
    Guard-->>UI: Return domain-specific story & generic rate metrics

    UI->>DoR: Evaluate Definition of Ready (O4)
    DoR->>DoR: Check readiness.yaml rules (user value, criteria, citations, gaps)
    DoR-->>UI: Return DoRVerdict (READY or BLOCKED with reasons)

    UI->>Gate: Create Draft record in PENDING state
    Gate->>DB: Save Draft (status = PENDING)

    rect rgb(240, 240, 240)
        note over PO,Gate: STRUCTURAL APPROVAL GATE (O9)
        PO->>UI: Click "Write to Tracker" on PENDING draft
        UI->>Gate: write_draft_to_tracker(draft_id)
        Gate-->>UI: ❌ REJECT: ApprovalRequiredError (Unapproved write blocked)

        PO->>UI: Review citations & open questions -> Click "Approve Draft"
        UI->>Gate: approve_draft(draft_id, actor="Human PO")
        Gate->>DB: Update Draft (status = APPROVED) & log ApprovalLog

        PO->>UI: Click "Write to Tracker" on APPROVED draft
        UI->>Gate: write_draft_to_tracker(draft_id)
        Gate->>Gate: Force status = NOT_READY & add tag ["AI-drafted"]
        Gate->>Tracker: create_item(payload, tags=["AI-drafted"], status="NOT_READY")
        Tracker-->>Gate: Return tracker record
        Gate->>DB: Update Draft (status = WRITTEN) & log WriteLog
        Gate-->>UI: ✅ SUCCESS: Record created at status NOT_READY
    end
```

---

## 🛡️ Key Architectural Principles & Safeguards

### 1. Structural Approval Gate & Status Floor (O9)
- **Service-Layer Gating**: External system writes (creating tracker issues or comments) cannot be triggered directly by LLM model outputs or prompt instructions.
- **State Machine Rules**:
  - `PENDING` draft write attempt -> Raises `ApprovalRequiredError`.
  - `REJECTED` draft write attempt -> Raises `ApprovalRequiredError`.
  - `WRITTEN` draft duplicate write attempt -> Raises `AlreadyWrittenError` (Idempotent safeguard).
- **Status Floor Locking**: When a human approves a draft and triggers a write to `MockTracker`, the service layer forces `status = NOT_READY` and adds tag `AI-drafted`. The LLM has zero permission to set a draft's status to `READY`.

### 2. Claim-Level Citation Verification (O6)
- **Existence Check**: Asserts section refs (`PB-04.1`) exist in `context_sections`. Whole-document citations are rejected as unresolvable.
- **Support Check**: Asserts section content supports the claimed requirement. Unsupported claims are placed in `unsupported_claims[]` and never hidden.

### 3. Deterministic Governance & Prioritization (O5)
- Prioritization scores are computed 100% in Python code via an explicit weighted arithmetic formula:
  $$\text{Base} = 0.40 \cdot \text{BV} + 0.25 \cdot \text{Urgency} + 0.20 \cdot \text{Risk} + 0.15 \cdot \text{Alignment}$$
  $$\text{Final} = \text{Base} \cdot \text{ReadinessFactor} \cdot (1 - 0.10 \cdot \text{DependencyPenalty})$$
- Sprint slices are sorted topologically so no story is proposed ahead of an unmet dependency.

---

## 🔌 Adapter Contracts & Swappability
All external data and provider connections use abstract Python `Protocol` or `ABC` interfaces:

1. **`LLMProvider` Protocol** (`app/llm/base.py`):
   - `GroqProvider` (`qwen/qwen3.6-27b` via REST API)
   - `MockProvider` (Offline deterministic mock for instant test suites)
2. **`Tracker` Protocol** (`app/adapters/tracker.py`):
   - `MockTracker` (Local in-memory / audit-logged tracker)
3. **`DocumentStore` Protocol** (`app/adapters/doc_store.py`):
   - `MockDocumentStore` (Markdown context loader)
