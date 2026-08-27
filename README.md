# PO Backlog Architect Agent — FlowDesk

An enterprise-grade Product Owner Agent that generates backlog artifacts while enforcing governance: unsupported requirements cannot silently become work, missing information is surfaced as open questions, DoR gates enforce readiness deterministically, and all AI-generated items require human approval before external writes — with a structural NOT_READY status floor.

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

| ID | Capability | Status | Evidence |
|----|------------|--------|----------|
| **O1** | Context Indexing | ✅ | TC-01, E2E-01 (step 1–3) |
| **O2** | Epic Decomposition | ✅ | TC-04, TC-08, E2E-01, E2E-03 |
| **O3** | Acceptance Criteria | ✅ | TC-02, E2E-01 (step 4) |
| **O4** | Definition of Ready | ✅ | TC-05, E2E-01 (step 7), E2E-03 |
| **O5** | Prioritization | ✅ | TC-06, E2E-01 (step 9) |
| **O6** | Grounding & Citations | ✅ | TC-01, E2E-01 (step 5), E2E-04, ADV-01, ADV-05 |
| **O7** | Overlap Detection | ✅ | TC-07, E2E-01 (step 8) |
| **O8** | Anti-Generic Guard | ✅ | TC-03, E2E-05, ADV-02, ADV-03 |
| **O9** | Approval Gate & Status Floor | ✅ | TC-09, E2E-01 (step 10), E2E-02, ADV-06, ADV-07, API tests |
| **O10** | Stakeholder Input Synthesis | *Not built* | Explicit scope cut — focus on robust MUST set |
| **O11** | Batch Criteria Generation | *Not built* | Single story & epic flows; bulk UI omitted |
| **O12** | Release Notes Extraction | *Not built* | Omitted per priority cut order |

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
| **TC-02** | Open-Question Recall (Planted Gaps) | 1.0 (3/3) | 1.0 (3/3) | 1.0 (3/3) | LLM-backed | **PASS** |
| **TC-03** | Generic Story Rate | ≤ 0.10 | 0.00 | 0.00 | Deterministic | **PASS** |
| **TC-04** | Decomposition Coverage | ≥ 0.85 | 1.00 | 1.00 | LLM-backed | **PASS** |
| **TC-05** | Readiness Gate Accuracy | 1.0 (4/4) | 1.0 (4/4) | 1.0 (4/4) | Deterministic | **PASS** |
| **TC-06** | Prioritisation Reproducibility | 1.0 | 1.0 | 1.0 | Deterministic | **PASS** |
| **TC-07** | Overlap Detection | True | True | True | Deterministic | **PASS** |
| **TC-08** | Thin Epic Behaviour | True | True | True | LLM-backed | **PASS** |
| **TC-09** | Approval Gate and Status Floor | True | True | True | Deterministic | **PASS** |
| **TC-10** | Glossary Consistency | True | True | True | Deterministic | **PASS** |
| **TOTAL** | **Golden Cases Pass Rate** | **10 / 10** | **100.0%** | **100.0%** | **Avg Latency 1.60s** | **PASS** |

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
# Set GROQ_API_KEY for live LLM evaluation
# LLM_PROVIDER=mock (default) or groq
```

### 3. Seed Database & FTS5 Index
```bash
python -m app.seed
```

### 4. Run Tests
```bash
# Unit tests (approval gate)
pytest tests/test_approval_gate.py -v

# API integration tests (HTTP status codes: 403/409)
pytest tests/test_api_integration.py -v

# End-to-end pipeline tests (5 scenarios)
pytest tests/test_e2e_pipeline.py -v

# All tests
pytest tests/ -v
```

### 5. Run Evaluation
```bash
# Deterministic regression (10/10 baseline)
python -m eval.run --provider mock

# Live LLM evaluation (3 runs per LLM-backed case)
python -m eval.run --provider groq --llm-runs 3

# Compare Mock vs Groq
python eval/compare.py

# Adversarial probes (7 scenarios)
python eval/adversarial_run.py
```

### 6. Launch UI & API
```bash
# FastAPI backend
uvicorn app.main:app --reload

# Streamlit dashboard (separate terminal)
streamlit run ui/dashboard.py
```

---

## 🏗️ Architecture & Component Boundaries

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

## 🤖 Declaration of AI Assistance & Tools Stack

This application and engineering submission were developed using an integrated AI engineering & research stack:
- **Primary Agentic IDE**: **Google Antigravity IDE** — Used for end-to-end agentic pair-programming, automated pytest execution, browser subagent UI testing, and documentation generation.
- **Live LLM Inference**: **Groq Free API (`qwen/qwen3.6-27b`)** — Primary open-weights LLM provider for live, low-latency structured JSON artifact generation.
- **Architectural & Conceptual Research**: **ChatGPT**, **Gemini**, **Perplexity**, **Manus**, and **Claude** — Used during Days 1–2 research for competitive benchmark design, prompt guard modeling, FTS5 retrieval strategy, and decision log validation.

All code, database schemas, gating logic, unit tests, evaluation scripts, and adversarial probes have been fully verified, executed, and committed locally.