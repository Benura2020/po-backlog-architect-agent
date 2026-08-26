# PO Backlog Architect Agent — Implementation Plan

This implementation plan outlines the architecture, data models, capabilities (O1–O9), evaluation harness, and execution steps for building the **PO Backlog Architect Agent** for Digital T3's AI Full Stack Engineer intern challenge.

The plan strictly adheres to all requirements from the 10 Excel tabs (`Notes/PO_Backlog_Architect_Agent_Intern_Challenge.xlsx`) and the finalized plan (`docs/4-day-plan.md`), guaranteeing **zero automatic failure triggers** and aiming for an **Exceptional (85+) score band**.

---

## User Review Required

> [!IMPORTANT]
> **LLM Provider Strategy**:
> We will implement a flexible `LLMProvider` adapter protocol supporting:
> 1. **Groq Provider** (`llama-3.3-70b-versatile`) — Fast execution, strict JSON schema output.
> 2. **Ollama Provider** (`qwen2.5:7b`) — Local execution fallback.
> 3. **Mock Provider** — Instant offline unit testing without external API calls or network dependency.

> [!IMPORTANT]
> **Approval Gate & Status Floor (Auto-Fail Safeguard)**:
> External system writes (tracker creation/comments) are **structurally gated in Python code** (`ApprovalService`), NOT in LLM system prompts.
> - Attempts to write `PENDING` or `REJECTED` drafts raise `ApprovalRequiredError`.
> - Written items are automatically tagged `AI-drafted` and forced to status `NOT_READY`. The LLM cannot set status to `READY`.

---

## Open Questions

> [!NOTE]
> 1. Do you have a **Groq API key** available in your local environment, or should we set up the **Mock LLM Provider** as the default fallback for local test runs?
> 2. Would you like to proceed step-by-step according to the Day 1 plan (Scaffolding, Seed Data, Adapters, SQLite Context Indexer, Citation Enforcement, Criteria Generator)?

---

## Proposed System Architecture

```
                                  Streamlit UI
                                       │
                             FastAPI Service Layer
                                       │
 ┌─────────────────────────────────────┴─────────────────────────────────────┐
 │                            Agent Engine Core                              │
 │  ┌─────────────────┐   ┌────────────────────┐   ┌──────────────────────┐  │
 │  │ Epic Decomposer │   │ Criteria Generator │   │ Anti-Generic Guard   │  │
 │  │     (O2)        │   │       (O3)         │   │        (O8)          │  │
 │  └────────┬────────┘   └─────────┬──────────┘   └──────────┬───────────┘  │
 │           │                      │                         │              │
 │  ┌────────┴────────┐   ┌─────────┴──────────┐   ┌──────────┴───────────┐  │
 │  │ Citation Engine │   │  DoR Gate (YAML)   │   │  Priority Engine     │  │
 │  │     (O6)        │   │       (O4)         │   │   (O5 Code Formula)  │  │
 │  └─────────────────┘   └────────────────────┘   └──────────────────────┘  │
 └─────────────────────────────────────┬─────────────────────────────────────┘
                                       │
 ┌─────────────────────────────────────┴─────────────────────────────────────┐
 │                          Adapters & Repositories                          │
 │  ┌────────────────┐   ┌─────────────────────┐   ┌──────────────────────┐  │
 │  │  LLM Provider  │   │ SQLite FTS5 Indexer │   │  MockTracker Adapter │  │
 │  │ (Groq/Mock/Oll)│   │   (O1 Context)      │   │  (O9 Write Audit Log)│  │
 │  └────────────────┘   └─────────────────────┘   └──────────────────────┘  │
 └───────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Components & File Modifications

### Component 1: Seed Data Infrastructure (`data/`)

#### [NEW] [product_brief.md](data/product_brief.md)
FlowDesk Internal Service Request Management Platform brief (15 sections, `PB-01` … `PB-15`), including 3 deliberate gaps:
1. File size limit ("Large files are rejected" — no limit specified)
2. Approver role ("Approvers can override rejected requests" — undefined role)
3. State transition ("Rejected submissions are returned" — undefined state/resubmission)
Plus 1 inconsistency ("Requester Owner" vs "Request Owner") and 1 backlog contradiction.

#### [NEW] [glossary.json](data/glossary.json)
20 domain terms for FlowDesk with canonical definitions.

#### [NEW] [backlog.json](data/backlog.json)
20 mixed-quality items (`BL-001` … `BL-020`), including 4 readiness test cases (`BL-003`, `BL-007`, `BL-012` blocked; `BL-005`, `BL-008` pass) and overlap target `BL-006`.

#### [NEW] [epics.json](data/epics.json)
`EP-001` (detailed document attachment epic) and `EP-002` (thin approval automation epic for Golden Case 8).

#### [NEW] [feedback.json](data/feedback.json)
Feedback entries with explicit consent true/false records.

---

### Component 2: Core Models, Schemas & Configuration (`app/schemas/`, `config/`)

#### [NEW] [domain.py](app/schemas/domain.py)
Pydantic v2 schemas:
- `Citation`: `source`, `ref`, `quote`
- `OpenQuestion`: `question`, `reason`, `missing_concept`
- `UnsupportedClaim`: `claim`, `citation`, `reason`
- `GWTCriterion`: `given`, `when`, `then`
- `AcceptanceCriteriaDraft`: `happy_path`, `alternatives`, `edge_cases`, `non_functional`, `open_questions`, `unsupported_claims`, `citations`
- `StoryDraft`: `title`, `description`, `rationale`, `citations`, `dependencies`, `unknowns`
- `DoRVerdict`: `status` (`READY` | `BLOCKED`), `checks` (list of `DoRCheck`), `blocking_reasons`, `suggested_actions`
- `PriorityScore`: `business_value`, `urgency`, `risk_reduction`, `strategic_alignment`, `dependency_penalty`, `readiness_factor`, `computed_score`, `rationale`
- `OverlapResult`: `target_story_id`, `existing_item_id`, `relationship_type` (`DUPLICATE` | `SUBSET` | `SUPERSET` | `ADJACENT`), `recommendation`, `confidence`

#### [NEW] [readiness.yaml](config/readiness.yaml)
YAML configuration defining the 6 Definition of Ready rules.

#### [NEW] [generic_guard.json](config/generic_guard.json)
List of forbidden generic phrases for the anti-generic guard.

---

### Component 3: LLM & Adapter Layer (`app/llm/`, `app/adapters/`)

#### [NEW] [base.py](app/llm/base.py)
Abstract `LLMProvider` base class and interface.

#### [NEW] [groq_provider.py](app/llm/groq_provider.py)
Groq LLM provider implementation with JSON schema retry support.

#### [NEW] [mock_provider.py](app/llm/mock_provider.py)
Deterministic Mock LLM provider returning structured JSON for offline eval and unit tests.

#### [NEW] [tracker.py](app/adapters/tracker.py)
`Tracker` protocol and `MockTracker` implementation.

#### [NEW] [doc_store.py](app/adapters/doc_store.py)
`DocumentStore` protocol for context documents.

---

### Component 4: Application Services & Agents (`app/services/`, `app/agents/`)

#### [NEW] [context_service.py](app/services/context_service.py)
SQLite FTS5 indexer for product brief, glossary, and backlog. Enables stable section ref lookup (`PB-04.2`) and keyword/semantic search (O1).

#### [NEW] [citation_service.py](app/services/citation_service.py)
Two-level citation enforcement engine (O6):
1. **Existence check**: Verifies section ref exists in DB.
2. **Support check**: Verifies section content supports the claim.

#### [NEW] [criteria_agent.py](app/agents/criteria_agent.py)
Structured acceptance criteria generator (O3) with forced `open_questions` surfacing for planted gaps.

#### [NEW] [decomposition_agent.py](app/agents/decomposition_agent.py)
Epic decomposition agent (O2). Produces grounded stories for detailed epics, and surfaces `questions > stories` for thin epics.

#### [NEW] [generic_guard_service.py](app/services/generic_guard_service.py)
Anti-generic story checker (O8). Evaluates story descriptions against forbidden patterns, triggers re-generation, and logs before/after metrics.

#### [NEW] [readiness_service.py](app/services/readiness_service.py)
Definition of Ready gate (O4). Checks configurable YAML rules and supports human override logging.

#### [NEW] [approval_service.py](app/services/approval_service.py)
Draft approval & status floor gate (O9). Structurally prevents writing non-approved drafts and forces status `NOT_READY` with tag `AI-drafted`.

#### [NEW] [prioritization_service.py](app/services/prioritization_service.py)
Deterministic prioritization engine (O5). Computes score from explicit formula and sorts backlog with topological dependency constraints.

#### [NEW] [overlap_service.py](app/services/overlap_service.py)
Overlap detection engine (O7). Identifies relationship type (`DUPLICATE`, `SUBSET`, etc.) and recommends merge options.

---

### Component 5: Data Persistence & Database (`app/db/`, `app/models/`)

#### [NEW] [database.py](app/db/database.py)
SQLAlchemy SQLite database setup.

#### [NEW] [models.py](app/models/models.py)
ORM models: `ContextSection`, `BacklogItem`, `Draft`, `ApprovalLog`, `WriteLog`.

---

### Component 6: FastAPI Application (`app/main.py`, `app/api/`)

#### [NEW] [main.py](app/main.py)
FastAPI application entry point.

#### [NEW] [routes.py](app/api/routes.py)
REST endpoints for context indexing, decomposition, criteria generation, readiness checking, prioritization, approval queue, and external writes.

---

### Component 7: Streamlit User Interface (`ui/`)

#### [NEW] [app.py](ui/app.py)
Streamlit multi-tab dashboard:
1. **Context & Search**: Browse sections, glossary, search brief with FTS5.
2. **Epic Decomposition**: Decompose detailed and thin epics.
3. **Criteria Generator**: Generate GWT criteria + view open questions & citations.
4. **Readiness Gate**: View DoR checklist & submit human overrides.
5. **Prioritization**: View visible scoring arithmetic & dependency-aware backlog slice.
6. **Approval Queue (Critical)**: List drafts, review citations/open questions, approve/reject, trigger gated write to MockTracker.
7. **Evaluation Harness**: Run `eval.run` live and display metric dashboard.

---

### Component 8: Evaluation Harness & Tests (`eval/`, `tests/`)

#### [NEW] [golden_cases.json](eval/golden_cases.json)
Golden test case definitions matching Golden Cases 1–10.

#### [NEW] [run.py](eval/run.py)
Executable evaluation harness script (`python -m eval.run`). Evaluates agent against all 10 Golden Cases and saves results to `eval/results.json`.

#### [NEW] [results.json](eval/results.json)
Committed output file from evaluation runs.

#### [NEW] [test_approval_gate.py](tests/test_approval_gate.py)
Unit tests asserting that pending and rejected drafts cannot be written to external systems (Golden Case 9).

#### [NEW] [test_grounding.py](tests/test_grounding.py)
Unit tests asserting citation resolution and open-question surfacing for planted gaps (Golden Cases 1 & 2).

---

## Day-by-Day Implementation Roadmap

### Day 1: Scaffolding, Data, Indexing, Grounding & Criteria (O1, O6, O3)
1. Initialize directory structure and seed FlowDesk sample dataset (`product_brief.md`, `glossary.json`, `backlog.json`, `epics.json`).
2. Build SQLite FTS5 context indexer (`ContextService`) supporting stable section refs (`PB-01` … `PB-15`).
3. Build two-level citation enforcement engine (`CitationService`).
4. Build structured criteria generator (`CriteriaAgent`) with mandatory open questions for planted gaps.

### Day 2: Decomposition, Anti-Generic Guard, DoR Gate & Initial Eval (O2, O8, O4)
1. Build epic decomposition agent (`DecompositionAgent`) handling detailed vs thin epics (`questions > stories`).
2. Implement anti-generic pattern guard (`GenericGuardService`) with before/after metric tracking.
3. Build Definition of Ready gate (`ReadinessService`) driven by `readiness.yaml`.
4. Initialize evaluation harness framework (`eval/run.py`) and wire initial Golden Cases (TC-01, TC-02, TC-03, TC-05, TC-08).

### Day 3: Approval Gate, Prioritization, Overlap & Streamlit UI (O9, O5, O7)
1. Build `ApprovalService` with structural approval enforcement, `NOT_READY` status floor, and `AI-drafted` tagging.
2. Implement deterministic prioritization formula (`PrioritizationService`) with visible breakdown and topological sorting.
3. Build overlap detection engine (`OverlapService`).
4. Assemble Streamlit dashboard (`ui/app.py`) with complete Approval Queue tab.

### Day 4: Evaluation, Hardening, Documentation & Verification
1. Execute full evaluation suite (`python -m eval.run`), verify all 10 Golden Cases, and commit `eval/results.json`.
2. Verify clean clone setup and complete end-to-end user workflows.
3. Update `README.md` with honest status table, setup guide, and evaluation results summary.
4. Prepare architecture note (`docs/architecture.md`) and decision log (`docs/decision-log.md`).

---

## Verification Plan

### Automated Verification
```bash
# 1. Run unit test suite
pytest tests/ -v

# 2. Run golden evaluation harness
python -m eval.run

# 3. Test API startup
uvicorn app.main:app --reload
```

### Manual Verification Steps
1. Launch Streamlit UI (`streamlit run ui/app.py`).
2. Search brief for "file upload" and verify `PB-04` section refs.
3. Generate acceptance criteria for a file-upload story and verify that the open question *"What is the maximum permitted file size?"* is surfaced with 0 invented numbers.
4. Attempt to write a `PENDING` draft in the Approval Queue tab -> verify write is blocked.
5. Approve the draft and click write -> verify mock tracker entry is created with status `NOT_READY` and tag `AI-drafted`.
