# Architecture Specification — PO Backlog Architect Agent

## System Overview
The PO Backlog Architect Agent is structured with clear separation between user interface, REST API routes, core agent reasoning, deterministic governance algorithms, adapter layers, and persistent storage.

```
                              Streamlit Dashboard (ui/app.py)
                                           │
                                 FastAPI (app/main.py)
                                           │
 ┌─────────────────────────────────────────┴─────────────────────────────────────────┐
 │                                 Core Agent Engine                                 │
 │  ContextService  │  CitationService  │  CriteriaAgent  │  DecompositionAgent      │
 │  (SQLite FTS5)   │  (Grounding)      │  (O3 GWT)       │  (O2 Epic Split)         │
 └─────────────────────────────────────────┬─────────────────────────────────────────┘
 │                                         │
 ┌─────────────────────────────────────────┴─────────────────────────────────────────┐
 │                           Governance & Gating Layer                               │
 │  ReadinessService (DoR YAML)  │  PrioritizationService (Formula)                 │
 │  ApprovalService (Structural Gate) ──► Status Floor (NOT_READY) ──► MockTracker   │
 └───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Structural Approval Gate & Status Floor

> [!IMPORTANT]
> The single most critical safety boundary in this system is the **Approval Service Gate** (`app/services/approval_service.py`).

1. **Service-Layer Enforcement**: External system writes (creating tracker issues or comments) cannot be triggered directly by LLM model outputs or prompt instructions.
2. **State Machine Safeguard**:
   - `PENDING` draft write attempt -> Raises `ApprovalRequiredError`.
   - `REJECTED` draft write attempt -> Raises `ApprovalRequiredError`.
   - `WRITTEN` draft duplicate write attempt -> Raises `AlreadyWrittenError` (Idempotent safeguard).
3. **Status Floor Locking**: When a human approves a draft and triggers a write to `MockTracker`, the service layer forces `status = NOT_READY` and adds tag `AI-drafted`. The LLM has zero permission to set a draft's status to `READY`.

---

## 🔌 Adapter Contracts & Swappability
All external data and provider connections use abstract Python `Protocol` or `ABC` interfaces:

1. **`LLMProvider` Protocol** (`app/llm/base.py`):
   - `GroqProvider` (`llama-3.3-70b-versatile` via REST API)
   - `MockProvider` (Offline deterministic mock for instant test suites)
2. **`Tracker` Protocol** (`app/adapters/tracker.py`):
   - `MockTracker` (Local in-memory / audit-logged tracker)
3. **`DocumentStore` Protocol** (`app/adapters/doc_store.py`):
   - `MockDocumentStore` (Markdown context loader)
