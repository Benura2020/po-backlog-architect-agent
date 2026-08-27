# PO Backlog Architect Agent — FlowDesk

An enterprise-grade Product Owner Agent that generates backlog artifacts while enforcing governance: unsupported requirements cannot silently become work, missing information is surfaced as open questions, DoR gates enforce readiness deterministically, and all AI-generated items require human approval before external writes — with a structural NOT_READY status floor.

---

## 🎬 Recorded Walkthrough (5–10 min)

**YouTube Demo Recording**: [https://youtu.be/OgDHHyAENtE](https://youtu.be/OgDHHyAENtE)

The recording is a genuine end-to-end run on sample data covering all 7 tabs. It includes two explicit edge case / failure demonstrations:

1. **Edge Case A — Unapproved Write Blocked (HTTP 403)**: Attempting to write a `PENDING` draft to MockTracker returns `HTTP 403 Forbidden: Draft must be APPROVED`. Demonstrates the service-layer approval gate cannot be bypassed.
2. **Edge Case B — Generic Story Detected & Rewritten**: Entering `"Manage my data efficiently"` triggers all 3 layers of the Anti-Generic Guard (`GENERIC` score=1) and auto-rewrites the story to a domain-specific FlowDesk story.

> No slides. Genuine live run on seeded sample data.

---

## 🏆 Verification Snapshot Scorecard

| Metric | Result | Target | Evidence |
|--------|-------:|-------:|----------|
| **Automated Tests** | **24 / 24** | 100% | 24 tests across service-level approval enforcement, HTTP integration, and 5 E2E governance scenarios |
| **Mock Golden Cases** | **10 / 10** | 100% | Deterministic regression harness (`eval/results_mock.json`) |
| **Live Groq Golden Cases** | **10 / 10** | 100% | 3 repeated runs against live model `qwen/qwen3.6-27b` (`eval/results_groq.json`) |
| **Average LLM Latency** | **1.60s** | < 5.0s | Measured across live HTTP completion calls |
| **Validation Failures / Retries** | **0 / 0** | 0 | Pydantic schema validation loop |
| **Adversarial Probes** | **7 / 7** | 100% | Hallucinated number, generic guard, thin epic, prompt injection (`eval/results_adversarial.json`) |
| **Secrets Isolation** | **CONFIRMED** | 100% | `.env` gitignored; zero credentials in git history |

---

## 🛡️ Architectural Core Principle: Why the LLM Cannot Directly Write to Tracker

```
                    Probabilistic LLM
                            │
                            ▼
                    Proposed Draft Payload
                            │
                            ▼
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
        Grounding       GenericGuard       DoR
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                     Human Approval
                            │
                            ▼
                     ApprovalService
            (Structural Gate: HTTP 403 / 409)
                            │
                            ▼
              Status Floor: NOT_READY + AI-drafted
                            │
                            ▼
                     External Tracker
```

> **Governance by Architecture**: The LLM generates proposed backlog artifacts but has **zero direct authority** over external system writes. The Python `ApprovalService` layer independently enforces the approval state machine and status floor (`NOT_READY` + `"AI-drafted"` tag), blocking unapproved writes with `HTTP 403 Forbidden` regardless of model output.

---

## 🎯 Capability Status Matrix

Every ✅ below is backed by a specific golden test case or test file. No claim is unverified.

| ID | Capability | Status | One-line note |
|----|------------|--------|---------------|
| **O1** | Context Indexing | ✅ Done | SQLite FTS5 BM25 index over 15 addressable product brief sections (`PB-01`…`PB-15`). TC-01, E2E-01 |
| **O2** | Epic Decomposition | ✅ Done | LLM decomposes epics into stories with citation grounding; thin epics surface open questions. TC-04, TC-08, E2E-01, E2E-03 |
| **O3** | Acceptance Criteria | ✅ Done | Given/When/Then criteria generated with planted gap detection and citation support. TC-02, E2E-01 |
| **O4** | Definition of Ready | ✅ Done | 6-rule YAML-configured DoR gate; BLOCKED stories display per-rule failure reasons. TC-05, E2E-03 |
| **O5** | Prioritization | ✅ Done | Deterministic weighted arithmetic formula + topological sprint sequencing. TC-06, E2E-01 |
| **O6** | Grounding & Citations | ✅ Done | Claim-level section verification; whole-document refs rejected; hallucinated numbers flagged. TC-01, E2E-04, ADV-01, ADV-05 |
| **O7** | Overlap Detection | ✅ Done | Jaccard-similarity overlap detector classifies DUPLICATE / SUBSET / SUPERSET / ADJACENT. TC-07, E2E-01 |
| **O8** | Anti-Generic Guard | ✅ Done | 3-layer guard (exact phrase → vague-verb regex → 6-dimension specificity score) with auto-rewrite. TC-03, E2E-05, ADV-02, ADV-03 |
| **O9** | Approval Gate & Status Floor | ✅ Done | Service-layer HTTP 403 gate; APPROVED writes forced to `NOT_READY` + `AI-drafted` tag. TC-09, E2E-02, ADV-06, ADV-07 |
| **O10** | Stakeholder Input Synthesis | ❌ Not built | Explicit scope cut — engineering depth prioritised over feature breadth. See `docs/decision-log.md` ADR-008 |
| **O11** | Batch Criteria Generation | ❌ Not built | Single story & epic flows; bulk UI omitted per scope cut. |
| **O12** | Release Notes Extraction | ❌ Not built | Omitted per priority cut order. |

---

## 🔬 Evaluation Strategy

This system uses **two evaluation modes** to provide both reproducibility and real-LLM evidence.

### Deterministic Regression (MockProvider)
Reproducible, offline, CI-safe. All 10 golden cases are deterministic against MockProvider.

```bash
python -m eval.run --provider mock
```

**Result: 10/10 (100%) — deterministic baseline**

### Live LLM Evaluation (GroqProvider)
Tests LLM-backed capabilities (TC-02, TC-04, TC-08) against the live `qwen/qwen3.6-27b` model on Groq.
LLM output is probabilistic — results are reported as observed, not guaranteed.

```bash
python -m eval.run --provider groq --llm-runs 3
```

Run `--llm-runs 3` to test stability across 3 independent runs per LLM-backed case.

### Comparison Report
```bash
python eval/compare.py
```
Side-by-side table: which cases pass on Mock vs Groq, with latency, retry count, and validation failures.

### Adversarial Evaluation
```bash
python eval/adversarial_run.py
```
7 adversarial probes: hallucinated numbers, generic stories, missing actors, thin epics, whole-document citations, LLM READY override, prompt-injection resistance.

---

## 📊 Golden Test Cases (Deterministic Regression)

| Case ID | Test Name | Target | Actual | Evidence Type | Verdict |
|---------|-----------|--------|--------|---------------|---------|
| **TC-01** | Citation Resolution | 0 unresolvable | 0 | Deterministic | **PASS** |
| **TC-02** | Open-Question Recall (Planted Gaps) | 1.0 (3/3) | 1.0 (3/3) | LLM-backed | **PASS** |
| **TC-03** | Generic Story Rate | ≤ 0.10 | 0.00 | Deterministic | **PASS** |
| **TC-04** | Decomposition Coverage | ≥ 0.85 | 1.00 | LLM-backed | **PASS** |
| **TC-05** | Readiness Gate Accuracy | 1.0 (4/4) | 1.0 (4/4) | Deterministic | **PASS** |
| **TC-06** | Prioritisation Reproducibility | 1.0 | 1.0 | Deterministic | **PASS** |
| **TC-07** | Overlap Detection | True | True | Deterministic | **PASS** |
| **TC-08** | Thin Epic Behaviour | True | True | LLM-backed | **PASS** |
| **TC-09** | Approval Gate and Status Floor | True | True | Deterministic | **PASS** |
| **TC-10** | Glossary Consistency | True | True | Deterministic | **PASS** |
| **TOTAL** | **Golden Cases Pass Rate** | **10 / 10** | **100.0%** | **Avg Latency 1.60s** | **PASS** |

*Verified Evidence: `eval/results_mock.json` (Mock 10/10) | `eval/results_groq.json` (Groq 10/10 3-run) | `eval/results_adversarial.json` (Adversarial 7/7)*

### 🧪 Automated Test Suite Summary
```text
pytest tests/ -v ──► 24/24 PASS (100%)
  ├── test_approval_gate.py    (Unit approval gate)
  ├── test_api_integration.py  (HTTP status codes: 403 Forbidden / 409 Conflict)
  └── test_e2e_pipeline.py     (5 E2E scenarios: Happy path, Bypass, Thin epic, Hallucination, Generic guard)
```

---

## ⚡ Auto-Fail Safeguards (Structurally Enforced)

1. **Approval Gate**: `ApprovalService` blocks PENDING/REJECTED external writes at the service layer — not in prompts. HTTP: `403 Forbidden`. Idempotency: `409 Conflict`.
2. **Status Floor**: All AI-generated tracker writes are locked at `NOT_READY` + tagged `AI-drafted`. LLM output claiming `READY` is silently overridden (proven in ADV-06).
3. **Citation Grounding**: Whole-document refs (e.g. `product_brief.md`) are rejected — only section refs (e.g. `PB-04.1`) accepted. Hallucinated facts that don't match section text are flagged.
4. **Anti-Generic Guard (3 layers)**: Exact phrase match → Vague-verb regex → Explainable specificity scoring with reasons.
5. **Prompt Injection Resistance**: Service-layer governance enforces NOT_READY regardless of LLM or context content (proven in ADV-07).
6. **Secrets Isolation**: API keys managed via `.env` (gitignored). Only `.env.example` committed.

---

## 🚀 Quickstart & Reproduction Guide

### 1. Clone & Install Dependencies
```bash
git clone <repository-url>
cd po-backlog-architect-agent
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and set your GROQ_API_KEY
# LLM_PROVIDER=mock  (default, no API key needed)
# LLM_PROVIDER=groq  (live AI inference, requires GROQ_API_KEY)
```

> **Model used**: `qwen/qwen3.6-27b` via Groq Free API

### 3. Seed Database & FTS5 Index
```bash
python -m app.seed
```

### 4. Launch UI & API
```bash
# Terminal 1 — FastAPI backend
uvicorn app.main:app --reload

# Terminal 2 — Streamlit dashboard
streamlit run ui/dashboard.py
```

Visit `http://localhost:8501` for the Streamlit dashboard.
Visit `http://localhost:8000/docs` for the FastAPI OpenAPI docs.

### 5. Run Tests
```bash
pytest tests/ -v
```

### 6. Run Evaluation Harness
```bash
# Deterministic regression (10/10 baseline, no API key needed)
python -m eval.run --provider mock

# Live LLM evaluation (requires GROQ_API_KEY)
python -m eval.run --provider groq --llm-runs 3

# Side-by-side comparison table
python eval/compare.py

# Adversarial probes (7 scenarios)
python eval/adversarial_run.py
```

---

## 🏗️ Architecture & Component Boundaries

See [`docs/architecture.md`](docs/architecture.md) for the full component diagram, sequence flow, and adapter contracts.

```
 Streamlit Dashboard (ui/dashboard.py) ──► FastAPI REST API (app/main.py)
                                           │
 ┌─────────────────────────────────────────┴─────────────────────────────────────────┐
 │                                Core Agent Engine                                  │
 │  ContextService  │  CitationService  │  CriteriaAgent  │  DecompositionAgent       │
 │  (SQLite FTS5)   │  (Grounding)      │  (O3 GWT)       │  (O2 Epic Split)          │
 └─────────────────────────────────────────┬─────────────────────────────────────────┘
                                           │
 ┌─────────────────────────────────────────┴─────────────────────────────────────────┐
 │                     Governance & Gating Layer (Structurally Enforced)              │
 │  GenericGuardService (3-layer)  │  ReadinessService (DoR YAML)                    │
 │  OverlapService  │  PrioritizationService (Formula)                               │
 │  ApprovalService (Gate) ──► Status Floor (NOT_READY) ──► Tracker Adapter          │
 │  HTTP: 403 PENDING/REJECTED  │  409 WRITTEN (idempotency)                         │
 └───────────────────────────────────────────────────────────────────────────────────┘

LLM Providers (adapter pattern):
  GroqProvider (live)  ←──► LLMProvider interface ←──► MockProvider (deterministic)
```

---

## 📁 Repository Structure

```
po-backlog-architect-agent/
├── app/
│   ├── adapters/        # External system adapters (tracker.py, doc_store.py)
│   ├── agents/          # LLM-backed agents (criteria_agent.py, decomposition_agent.py)
│   ├── llm/             # LLM provider abstraction (base.py, groq_provider.py, mock_provider.py)
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic domain schemas
│   ├── services/        # Core governance services (approval_service.py, readiness_service.py, ...)
│   ├── seed.py          # Database seeder (run: python -m app.seed)
│   └── main.py          # FastAPI app entrypoint
├── config/
│   ├── readiness.yaml   # Definition of Ready rules
│   └── generic_guard.json  # Anti-Generic Guard forbidden phrases
├── data/
│   ├── product_brief.md # Product context (15 addressable sections PB-01…PB-15)
│   ├── backlog.json     # 20 sample backlog items (BL-001…BL-020)
│   ├── epics.json       # 2 epics (EP-001 detailed, EP-002 thin)
│   ├── glossary.json    # 20 domain glossary terms
│   └── feedback.json    # Stakeholder feedback data
├── eval/
│   ├── run.py           # Evaluation harness (10 golden cases)
│   ├── adversarial_run.py  # Adversarial probes (7 scenarios)
│   ├── compare.py       # Mock vs Groq comparison report
│   ├── golden_cases.json   # Test case definitions
│   ├── results_mock.json   # Mock provider results (committed)
│   ├── results_groq.json   # Groq live results (committed)
│   └── results_adversarial.json  # Adversarial probe results (committed)
├── tests/
│   ├── test_approval_gate.py    # Unit: approval gate enforcement
│   ├── test_api_integration.py  # Integration: HTTP 403/409 status codes
│   └── test_e2e_pipeline.py     # E2E: 5 pipeline scenarios
├── ui/
│   └── dashboard.py     # Streamlit 7-tab dashboard
├── docs/
│   ├── architecture.md         # Architecture notes & diagrams
│   ├── decision-log.md         # Decision & assumption log (ADR-001…ADR-008)
│   ├── evaluation-report.md    # Full evaluation results & methodology
│   ├── user-guide.md           # Tab-by-tab UI walkthrough with screenshots
│   ├── final-engineering-report.md  # 4-day timeline, design rationale, 7-day roadmap
│   └── images/                 # UI screenshots (tab1…tab7)
├── .env.example         # Environment variable template
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

---

## 🌟 Stretch Work

> Noted separately as stretch — scored only after all MUST capabilities are genuinely done.

The following were implemented **beyond** the 9 MUST capabilities:

| Stretch Item | What was built |
|---|---|
| **3-Layer Anti-Generic Guard with Auto-Rewrite** | Full 3-layer specificity detection (phrase match → regex → 6-dimension scoring) plus automatic domain-specific story rewriting (O8 extended) |
| **Adversarial Probe Suite (7 scenarios)** | A dedicated `eval/adversarial_run.py` suite testing hallucinated numbers, generic evasion, missing actors, thin epics, whole-doc citations, LLM READY override, and prompt injection resistance |
| **Dual-Provider Evaluation Framework** | `MockProvider` + `GroqProvider` with `--llm-runs N` for stability testing, plus side-by-side `compare.py` report |
| **Human Override Audit Log** | Immutable `ApprovalLogModel` records every human override of a BLOCKED story with actor, timestamp, and justification |
| **Idempotency Guard** | `HTTP 409 Conflict` on duplicate tracker write prevents double-creating already-written drafts |

---

## 🤖 Declaration of AI Assistance & Tools Stack

This application and engineering submission were developed using an integrated AI engineering & research stack:
- **Primary Agentic IDE**: **Google Antigravity IDE** — Used for end-to-end agentic pair-programming, automated pytest execution, browser subagent UI testing, and documentation generation.
- **Live LLM Inference**: **Groq Free API (`qwen/qwen3.6-27b`)** — Primary open-weights LLM provider for live, low-latency structured JSON artifact generation.
- **Architectural & Conceptual Research**: **ChatGPT**, **Gemini**, **Perplexity**, **Manus**, and **Claude** — Used during Days 1–2 research for competitive benchmark design, prompt guard modeling, FTS5 retrieval strategy, and decision log validation.

All code, database schemas, gating logic, unit tests, evaluation scripts, and adversarial probes have been fully verified, executed, and committed locally.