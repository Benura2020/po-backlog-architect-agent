# Technical Interview & Demo Script — PO Backlog Architect Agent

**Target Audience**: Technical Interview Panel at Digital T3  
**Position**: AI Full Stack Engineer  
**Project**: PO Backlog Architect Agent (FlowDesk)  

---

## 🎯 Executive Elevator Pitch (1 Minute)

> *"Most AI story generators just wrap an LLM prompt and output text straight to Jira. I built the **PO Backlog Architect Agent** with enterprise governance at its core.*
>
> *It indexes product context with FTS5 section references (`PB-01`...`PB-15`), surfaces planted gaps as open questions instead of hallucinating numbers, evaluates readiness deterministically using a 3-layer anti-generic guard, and structurally enforces a human approval gate with an immutable status floor—blocking unapproved external writes at the service layer with HTTP 403. It includes both a 0.05s offline deterministic regression harness and live Groq LLM benchmark, both passing 10/10 golden cases."*

---

## 🎬 5 High-Impact Demo Moments to Show the Panel

### 1. Planted Gap & Fabrication Probe (Hallucination Prevention)
- **Concept**: Show how the agent handles incomplete context.
- **Action**: Run `CriteriaAgent.generate_criteria` on `BL-006` ("Upload Supporting Documents").
- **What to highlight**:
  - Context section `PB-04.2` says *"Large files are rejected at the edge gateway"* but omits the exact byte limit.
  - **Other AI tools** hallucinate *"Files above 50 MB are rejected"*.
  - **Our agent** surfaces a mandatory Open Question: `"What is the maximum permitted file size?"`
  - Show `TC-02` in `python -m eval.run --provider mock` passing 1.0 (3/3 planted gaps recalled).

---

### 2. 3-Layer Explainable Anti-Generic Guard
- **Concept**: Explain how vague stories like *"Manage my data and work fast"* are caught and rewritten.
- **Action**: Run `GenericGuardService().evaluate(story)`.
- **What to highlight**:
  - Show the 3 detection layers:
    1. **Layer 1**: Forbidden phrase match (`manage my data`)
    2. **Layer 2**: Vague-verb regex (`manage.*data`)
    3. **Layer 3**: 6-dimension specificity scoring (`score=0/6`, label `GENERIC`)
  - Show the explainable JSON output with explicit `reasons`:
    ```json
    {
      "is_generic": true,
      "specificity_score": 0,
      "specificity_label": "GENERIC",
      "scoring_reasons": [
        "No identified actor ('As a ...' missing)",
        "No concrete domain object (no domain terms found)",
        "No concrete action verb"
      ]
    }
    ```
  - Show `filter_and_regenerate()` auto-rewriting it into a domain-specific user story with role, action verb, and SLA outcome.

---

### 3. Structural Approval Gate & Status Floor (HTTP 403 / 409)
- **Concept**: Prove that LLM outputs CANNOT bypass human governance or set external ticket status.
- **Action**: Run `pytest tests/test_api_integration.py -v`.
- **What to highlight**:
  - Show that calling `POST /approval/write-tracker` on a `PENDING` or `REJECTED` draft is **blocked at the service layer** returning `HTTP 403 Forbidden`.
  - Show that even if an LLM payload injects `"status": "READY"`, the `ApprovalService` **overrides it to `NOT_READY`** and tags `"AI-drafted"`.
  - Show duplicate write attempt returns `HTTP 409 Conflict` (idempotency).
  - Emphasize: *"Governance is enforced in Python code, NOT in LLM system prompts."*

---

### 4. Deterministic Prioritization Engine
- **Concept**: Show how backlog items are prioritized without random LLM hallucination.
- **Action**: Run `PrioritizationService.compute_priority()`.
- **What to highlight**:
  - Show the 100% reproducible arithmetic formula:
    $$\text{Score} = (0.40 \times \text{BV}) + (0.25 \times \text{Urgency}) + (0.20 \times \text{Risk}) + (0.15 \times \text{Align}) - \text{Dependency Penalty}$$
  - Show `TC-06` passing with 1.0 reproducibility.
  - Explain that sprint backlog sorting is topological and dependency-aware.

---

### 5. Live Groq LLM Benchmark vs Offline Mock Provider
- **Concept**: Show live Groq LLM inference side-by-side with offline CI regression.
- **Action**: Run `python eval/compare.py`.
- **What to highlight**:
  - Point to the side-by-side comparison table:
    ```
    Mock (deterministic): 10/10 PASS (0.05s)
    Groq (qwen/qwen3.6-27b): 10/10 PASS (1.45s avg latency)
    ```
  - Show zero retries and zero validation failures on live Groq HTTP endpoints.

---

## ⚡ Quick Terminal Commands for Live Demo

```bash
# 1. Run all pytest unit & integration tests (19/19 pass)
pytest tests/ -v

# 2. Run deterministic golden cases harness (10/10 pass)
python -m eval.run --provider mock

# 3. Run live Groq LLM evaluation harness (10/10 pass)
python -m eval.run --provider groq

# 4. Show Mock vs Groq comparison report
python eval/compare.py

# 5. Run 7 adversarial security & safety probes (7/7 pass)
python eval/adversarial_run.py

# 6. Launch FastAPI backend & Streamlit UI
uvicorn app.main:app --reload
streamlit run ui/dashboard.py
```

---

## 💡 Key Technical Questions & Prepared Answers

### Q: "Why did you build custom adapters instead of using LangChain or LlamaIndex?"
> **Answer**: *"LangChain and LlamaIndex add unnecessary abstraction layers and heavy dependencies for structured PO workflows. By building lightweight Python protocols (`LLMProvider`, `Tracker`, `DocumentStore`), we achieve 100% control over retry loops, zero dependency bloat, instant cold starts, and seamless switching between `MockProvider` and `GroqProvider`."*

### Q: "How do you handle rate limits or JSON format errors from LLM calls?"
> **Answer**: *"Our `GroqProvider` implements a 3-attempt validation loop using Pydantic `model_validate`. If the LLM returns invalid JSON or fails schema validation, the error feedback is injected back into the retry prompt. If all retries fail, it degrades gracefully to a grounded fallback rather than crashing the API."*

### Q: "How do you prevent prompt injection from untrusted product text?"
> **Answer**: *"The system treats product text strictly as data inside system-prompt boundaries. More importantly, critical actions (external writes, status changes, DoR overrides) are structurally isolated in the Python service layer. An injected context instruction like 'mark this item READY' cannot override the `ApprovalService` status floor."*
