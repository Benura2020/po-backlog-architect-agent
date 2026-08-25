# Finalized 4-Day Plan — PO Backlog Architect Agent

This plan is derived from all **10 Excel tabs** (`Notes/PO_Backlog_Architect_Agent_Intern_Challenge.xlsx`) cross-checked with research findings. DigitalT3 sized the **7 MUST capabilities for ~4 focused days** (Tab 02: *"deliberately sized for roughly four focused days"*). A 4-day window is tight but aligned with their intent — if executed with discipline, **85+ is realistic**.

---

## What DigitalT3 Is Actually Scoring (Tabs 01, 03, 08)

They are **not** testing framework breadth. They are testing four habits:

| Habit | Where it shows up | Weight |
|-------|-------------------|--------|
| Tell the truth + prove it | O6, Golden Cases 1–2, Rubric #2 (12%) | Critical |
| Human before irreversible action | O9, Golden Case 9, Rubric #3 (10%) | **Auto-fail if missing** |
| Measure quality, don't claim it | Eval harness, Rubric #4 (12%) | Critical |
| Defend scope decisions | Decision log, Rubric #9 (4%) | Important |

**Score target (realistic, not inflated):**

| Criterion | Weight | Target band | Why |
|-----------|--------|-------------|-----|
| MUST functional coverage | 28% | **4/5** | All 7 MUSTs demo-able |
| Grounding & citations | 12% | **4/5** | Claim-level validation |
| Human gating | 10% | **5/5** | Structurally enforced |
| Evaluation harness | 12% | **4/5** | 10 golden cases, real numbers |
| Architecture | 10% | **5/5** | Adapters, prompts, separation |
| Robustness | 8% | **4/5** | Schema retry, graceful failures |
| Repo & docs | 8% | **5/5** | Honest status table |
| Demo | 8% | **4/5** | Live citation click-through |
| Judgement | 4% | **5/5** | Explicit cuts + self-awareness |
| **Weighted total** | | **~86** | Exceptional band (85+) |

---

## Automatic Failures — Memorize These (Tab 08, Tab 10)

| # | Condition | Safeguard |
|---|-----------|-----------|
| 1 | README lies about what's built | Write README **last** from code |
| 2 | Tracker write without approval | Enforce in **service layer**, not prompt |
| 3 | Secrets in git | `.env` gitignored, `.env.example` only |
| 4 | Can't explain your code | Understand every file; delete what you can't defend |
| 5 | Fake eval numbers | `python -m eval.run` must reproduce README claims |

---

## Locked Technical Decisions (Tab 04 — with options)

### Primary stack (recommended — move fastest)

```
Python 3.11+  |  FastAPI  |  Pydantic v2  |  SQLAlchemy  |  SQLite + FTS5
Streamlit     |  pytest    |  httpx         |  pydantic-settings
```

### LLM strategy (Option A recommended for 4 days)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **A: Groq primary + Ollama fallback** | Fast, good quality, easy structured output | Needs API key; reviewer may not reproduce | **Use for dev** |
| **B: Ollama only** | Zero cost, fully reproducible | Weaker models, slower iteration | **Fallback + README note** |

**Implementation rule:** One `LLMProvider` protocol; never hard-code Groq.

```python
# .env.example
LLM_PROVIDER=groq          # or ollama
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile   # document exact version
OLLAMA_MODEL=qwen2.5:7b
```

### What NOT to build (Tab 01, Tab 10)

No Jira/Confluence, no vector DB, no LangGraph/LangChain, no auth, no React polish, no Docker unless setup breaks.

---

## Sample Product: FlowDesk (Tab 07 requirements)

**Product:** FlowDesk — Internal Service Request Management Platform

### Required seed data (commit all of this Day 1)

| Asset | Spec (Tab 07) | Target |
|-------|---------------|--------|
| Product brief | 1,500–3,000 words, numbered sections | 15 sections, IDs `PB-01` … `PB-15` |
| Glossary | 15–25 terms | 20 terms |
| Backlog | 15–25 mixed-quality items | 20 items (`BL-001` … `BL-020`) |
| Epics | 1 detailed + 1 thin | `EP-001` (detailed), `EP-002` (thin) |
| Feedback | 1 with consent + 1 without | For O10 stretch only |
| Deliberate gaps | 3 silences | See below |
| Inconsistency | 1 term brief ≠ glossary | "Requester Owner" vs "Request Owner" |
| Contradiction | 1 brief vs backlog | Draft editable vs BL-014 submitted editable |

### Three planted gaps (Golden Case 2 — most important metric)

| Gap | Brief says | Must NOT invent | Open question expected |
|-----|-----------|-----------------|------------------------|
| File size | "Large files are rejected" | "50 MB" | What is the maximum permitted file size? |
| Approver role | "Approvers can override rejected requests" | Role name | Which role is authorized as approver? |
| State transition | "Rejected submissions are returned for correction" | Target state | Which state? Is resubmission permitted? |

### Four readiness test stories (Golden Case 5)

| ID | Quality | Expected DoR |
|----|---------|--------------|
| BL-003 | No acceptance criteria | **BLOCKED** — missing criteria |
| BL-007 | Generic: "Users can upload files" | **BLOCKED** — not testable |
| BL-012 | "Approvers can review" — no role/outcome | **BLOCKED** — blocking questions |
| BL-005 | Complete, grounded | **PASS** |
| BL-008 | Complete, grounded | **PASS** |

### Overlap seed (Golden Case 7)

- `BL-006`: "Upload supporting documents to a request"
- Epic `EP-001` will produce a story that **subsets** this → flag as `SUBSET`, recommend merge

---

## Architecture (Tab 05)

```
Streamlit UI
     │
FastAPI (thin routes only)
     │
┌────┴────────────────────────────────────┐
│              Agent Pipeline              │
│  Decompose → Criteria → Validate → DoR  │
│       ↑           ↑          ↑           │
│   LLMProvider  Citation  GenericGuard    │
└────┬────────────────────────────────────┘
     │
┌────┴──────────┬──────────────┬──────────┐
│ Context/FTS5  │ PriorityEngine│ Overlap   │
│ (O1)          │ (O5, code)    │ (O7)      │
└────┬──────────┴──────────────┴──────────┘
     │
ApprovalService → Tracker Protocol → MockTracker
     │                                    │
Drafts DB                          write_log (audit)
```

**Core principle (Tab 01 design notes):**

> **LLM proposes → System verifies → Human approves**

| Probabilistic (LLM) | Deterministic (code) |
|---------------------|----------------------|
| Decomposition language | Citation existence + content check |
| Acceptance criteria drafting | Priority arithmetic |
| Rationale sentences | DoR checklist evaluation |
| Overlap semantic comparison | Approval gate + status floor |
| | Idempotent writes + audit log |

---

## Folder Structure

```
po-backlog-architect-agent/
│
├── app/
│   ├── main.py
│   ├── api/routes/
│   ├── agents/
│   ├── services/
│   ├── llm/
│   ├── adapters/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   └── core/
│
├── prompts/
├── data/
├── eval/
├── tests/
├── ui/
├── docs/
│   ├── 4-day-plan.md          ← this file
│   ├── architecture.md
│   └── decision-log.md
│
├── config/
│   ├── readiness.yaml
│   └── generic_guard.json
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Capability Priority & Cut Order (Tab 02, Tab 06)

### Build order (non-negotiable)

```
O1 → O6 → O3 → O2 → O4 → O9 → O5 → O8 → O7 → (O10 if time)
```

### If you fall behind — cut in this exact order

```
KEEP ALWAYS: O1, O6, O3, O2, O4, O9, O5
CUT FIRST:   O7 (overlap)
CUT SECOND:  O8 (anti-generic — but try hard; Golden Case 3)
NEVER CUT:   O9 (auto-fail territory)
SKIP:        O10, O11, O12 — mark "Not built" in README
```

---

# DAY-BY-DAY PLAN

---

## DAY 1 — Foundation + Context + Grounding + Criteria

**Excel mapping:** Tab 06 Day 1 + Day 2 (first half)  
**End state:** Story → grounded criteria with open questions (thin vertical slice)

### Morning (3–4 hrs): Repo + contracts + sample data

**Deliverables:**

- [ ] Git repo initialized with meaningful first commit
- [ ] Folder structure
- [ ] `requirements.txt`, `.env.example`, `.gitignore`, `pyproject.toml`
- [ ] **Sample data committed** — this is evaluation infrastructure, not filler:
  - `data/product_brief.md` (1,500–3,000 words, all gaps planted)
  - `data/glossary.json`
  - `data/backlog.json`
  - `data/epics.json`
  - `data/feedback.json` (consent true/false records)
- [ ] `docs/decision-log.md` — first entry: stack choices

**Database schema (Day 1):**

```
context_sections  |  backlog_items  |  drafts  |  approval_log  |  write_log
```

**Adapter interfaces (Day 1 — Tab 05):**

```python
class Tracker(Protocol): list_items, get_item, add_comment, create_item, transition
class DocumentStore(Protocol): get_document, list_sections
# + MockTracker, MockDocumentStore
```

### Midday (3 hrs): O1 — Load and index product context

**Requirements (Tab 02 O1):**

- Parse markdown headings → stable refs (`PB-01`, `PB-04.2`)
- Store in SQLite with FTS5
- Every chunk addressable; whole-document citations rejected

**API:**

```
POST /context/index     # load brief + glossary + backlog
GET  /context/search?q=file upload
GET  /context/sections/{ref}
```

**Day 1 O1 done when:** Search "file upload" returns `PB-04`, `PB-04.1`, etc.

### Afternoon (3 hrs): O6 — Citation enforcement (hard validation)

**Two-level validation:**

1. **Existence:** Does `PB-04.2` exist in indexed context?
2. **Support:** Does section text actually contain the claimed fact?

```json
{
  "claim": "Large files are rejected above 50 MB",
  "citation": {"source": "product_brief", "ref": "PB-04.2"},
  "valid": false,
  "reason": "Source mentions rejection but specifies no size limit"
}
```

Unsupported claims → `unsupported_claims[]`, never shipped silently (Tab 02 O6).

### Evening (3 hrs): O3 — Acceptance criteria + LLM abstraction

**Pydantic schema (required fields — Tab 01 design note):**

```python
class AcceptanceCriteriaDraft(BaseModel):
    happy_path: list[GWTCriterion]
    alternatives: list[GWTCriterion]
    edge_cases: list[GWTCriterion]
    non_functional: list[GWTCriterion]
    open_questions: list[OpenQuestion]      # REQUIRED, not optional
    unsupported_claims: list[UnsupportedClaim]
    citations: list[Citation]
```

**Pipeline:** LLM → JSON → Pydantic validate → retry (max 3) → citation validate

**Prompts:** `prompts/criteria_v1.txt` (versioned file, not inline)

**Day 1 end-to-end test:**

```
Input:  BL-005 (good story)
Output: GWT criteria, all citations resolve, 0 invented specifics

Input:  story touching file upload
Output: open question "What is maximum file size?" — NOT "50 MB"
```

**Commit messages today:**

```
chore: initialize project architecture
feat: add FlowDesk sample product data with deliberate gaps
feat: implement context indexing with addressable section refs
feat: add citation validation layer
feat: add structured acceptance criteria generation with open questions
```

---

## DAY 2 — Decomposition + Anti-Generic + DoR + Eval Start

**Excel mapping:** Tab 06 Day 2 (second half) + Day 3 + Day 4 (first half)  
**End state:** Epic → stories → criteria → DoR verdict; golden cases 1–5 wired

### Morning (3 hrs): O2 — Epic decomposition

**Reuse:** context retrieval + citation validator + schema retry

**Story output schema:**

```python
class StoryDraft(BaseModel):
    title: str
    description: str          # "As a [role], I want..."
    rationale: str            # why this story exists
    citations: list[Citation]
    dependencies: list[str]   # other story IDs
    unknowns: list[OpenQuestion]
```

**Rules in prompt (Tab 02 O2):**

- No implementation tasks
- No invented roles/limits/fields
- Ungrounded capabilities → gaps, not stories
- Thin epic: **questions > stories** (Golden Case 8)

**API:** `POST /epics/{id}/decompose`

### Midday (2 hrs): O8 — Anti-generic guard (SHOULD but high ROI)

**Configurable forbidden patterns** in `config/generic_guard.json`:

```json
{"forbidden_patterns": ["manage my data", "use the application efficiently"]}
```

**Flow:** Generate → pattern check → regenerate with failure feedback → surface persistent failures

**Measure and record:**

```
generic_rate_before_guard: X.XX
generic_rate_after_guard:  X.XX   (target < 0.10)
```

### Afternoon (3 hrs): O4 — Definition of Ready

**Checklist as config** — `config/readiness.yaml` (NOT hard-coded):

```yaml
criteria:
  - id: clear_user_value
  - id: testable
  - id: grounded
  - id: dependencies_known
  - id: no_blocking_questions
  - id: has_acceptance_criteria
```

**Output per story:**

```
VERDICT: BLOCKED
✗ no_blocking_questions — Approver role undefined (PB-06)
✗ grounded — Citation PB-99 does not exist
RESOLUTION: Define approver role; fix citation
```

**Human override:** logged with actor, reason, timestamp (Tab 02 O4)

**API:** `POST /stories/readiness` (single + batch)

### Evening (3 hrs): Start evaluation harness (Tab 07 — start Day 2, not Day 7)

**Create:** `eval/golden_cases.json`, `eval/run.py`, `eval/metrics.py`

**Wire today (minimum):**

| Case | Metric |
|------|--------|
| TC-01 | Citation resolution count = 0 |
| TC-02 | Open-question recall 3/3, invented-specific = 0 |
| TC-03 | Generic rate before/after guard |
| TC-05 | Readiness 4/4 |
| TC-08 | Thin epic: questions > stories |

Run: `python -m eval.run` — commit `eval/results.json` even if failing (honesty scores).

**Day 2 done when:**

- `EP-001` decomposes into grounded, non-overlapping stories
- `EP-002` (thin) produces more questions than stories
- DoR blocks BL-003, BL-007, BL-012; passes BL-005, BL-008
- Eval harness runs and prints metrics

---

## DAY 3 — Approval Gate + Prioritization + Overlap

**Excel mapping:** Tab 06 Day 4 (second half) + Day 5  
**End state:** Full MUST set complete; approval structurally enforced

### Morning (4 hrs): O9 — Draft to tracker (**most critical engineering block**)

**Draft state machine:**

```
PENDING → APPROVED → WRITTEN
        → REJECTED (terminal)
```

**Structural enforcement (Tab 01 — status floor):**

```python
def write_to_tracker(draft_id: str):
    draft = repo.get_draft(draft_id)
    if draft.status != DraftStatus.APPROVED:
        raise ApprovalRequiredError()
    if draft.status == DraftStatus.WRITTEN:
        raise AlreadyWrittenError()  # idempotency

    item = tracker.create_item(
        payload=draft.payload,
        tags=["AI-drafted"],
        status="NOT_READY"  # LLM cannot override this
    )
    repo.mark_written(draft_id, item.id)
    write_log.append(...)
```

**Tests (Golden Case 9 — must pass):**

- Pending → write: **FAIL**
- Rejected → write: **FAIL**
- Approved → write: **SUCCESS**, tagged, NOT_READY
- Approved → write again: **no duplicate** (exactly 1 record)

**Streamlit Approval Queue** (Tab 04: "real marks for usable approval queue"):

- List pending drafts
- Show story, citations (clickable → source section), open questions
- Approve / Reject with reason
- Attempt write on pending → show error

### Midday (3 hrs): O5 — Prioritization (100% deterministic code)

**Inputs per item (visible in UI):**

```
Business Value:       1-10
Urgency:              1-10
Risk Reduction:       1-10
Strategic Alignment:  1-10
Dependency Penalty:   0/1
Readiness Factor:     0/1 (blocked = 0)
```

**Formula (document in README + decision log):**

```
Base = (0.40 × BV) + (0.25 × Urgency) + (0.20 × Risk) + (0.15 × Alignment)
Final = Base × ReadinessFactor × (1 - 0.1 × DependencyPenalty)
```

**LLM only writes:** one-line rationale sentence

**Sprint slice:** topological sort — never propose ST-005 before ST-002 if dependency exists

**Golden Case 6:** hand-recompute 3 scores; perturb one input; verify rank direction

### Afternoon (3 hrs): O7 — Overlap detection (SHOULD — cut first if behind)

**Relationship types:** `duplicate | subset | superset | adjacent`

**Output:**

```
OVERLAP: ST-018 "Upload documents" ↔ BL-006 "Upload supporting documents"
Relationship: SUBSET
Recommendation: Merge — human decides
```

**Golden Case 7:** BL-006 flagged; 4 distinct stories not flagged

### Evening (2 hrs): Complete eval harness + Streamlit pages

**Wire remaining cases:**

| Case | What to assert |
|------|----------------|
| TC-04 | Decomposition coverage + redundancy |
| TC-06 | Priority reproducibility + dependency order |
| TC-07 | Overlap precision/recall |
| TC-09 | Approval gate automated tests |
| TC-10 | Glossary term preferred; inconsistency raised as open question |

**Streamlit tabs (functional > pretty):**

Context | Backlog | Decompose | Criteria | Readiness | Priority | Overlap | **Approval Queue** | Evaluation

**Day 3 done when:** All 7 MUST capabilities demo end-to-end on sample data.

---

## DAY 4 — Harden + Measure + Document + Demo

**Excel mapping:** Tab 06 Day 6 + Day 7 + Tab 09 Submission Checklist  
**End state:** Submittable repo; reproducible eval; 5–10 min recording

### Morning (3 hrs): Fix eval failures — do NOT fake numbers

```bash
pytest tests/
python -m eval.run
```

**Target metrics (Tab 07):**

| Metric | Target | Priority |
|--------|--------|----------|
| Citation resolution failures | 0 | MUST |
| Open-question recall | 3/3 | **Most important** |
| Invented-specific count | 0 | MUST |
| Generic rate (after guard) | < 0.10 | SHOULD |
| Readiness accuracy | 4/4 | MUST |
| Priority reproducibility | 3/3 | MUST |
| Approval gate | 100% pass | MUST |
| Thin epic | questions > stories | MUST |
| Overlap precision/recall | high | SHOULD |

**If a metric fails:** fix implementation OR document honestly in README limitations. A harness revealing a weakness you explain scores **higher** than fake passes (Tab 07).

### Midday (2 hrs): Clean clone test (Tab 09)

```bash
git clone <repo>
cd po-backlog-architect-agent
pip install -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY
python -m app.seed      # one command seeds all data
uvicorn app.main:app --reload &
streamlit run ui/app.py
python -m eval.run
```

Fix anything that breaks on fresh clone.

### Afternoon (3 hrs): Documentation (write FROM code, not aspirations)

**Required deliverables (Tab 09):**

| File | Content |
|------|---------|
| `README.md` | Status table (Done/Partial/Not built per capability), setup, eval results quoted |
| `docs/architecture.md` | Diagram, component boundaries, approval gate location |
| `docs/decision-log.md` | Scope cuts, LLM vs code split, FTS5 vs vector DB, formula choice |
| `eval/results.json` | Committed output from final `eval.run` |

**README status table (first thing reviewers read after code):**

| ID | Capability | Status | Notes |
|----|------------|--------|-------|
| O1 | Context indexing | Done | FTS5, PB-XX refs |
| O2 | Epic decomposition | Done | |
| O3 | Acceptance criteria | Done | Open questions required field |
| O4 | Definition of Ready | Done | YAML config, override logged |
| O5 | Prioritization | Done | Deterministic formula |
| O6 | Grounding/citations | Done | Existence + support check |
| O7 | Overlap detection | Done/Partial/Not built | Be honest |
| O8 | Anti-generic guard | Done/Partial | Report before/after rates |
| O9 | Draft to tracker | Done | Idempotent, status floor |
| O10 | Stakeholder synthesis | Not built | |
| O11 | Batch criteria | Not built | |
| O12 | Release notes | Not built | |

### Evening (2–3 hrs): Record demo (Tab 06 Day 7 script — 7 minutes)

| Time | Show |
|------|------|
| 0:00–0:30 | Repo overview + architecture diagram |
| 0:30–1:15 | Context loaded: 15 sections, 20 glossary, 20 backlog |
| 1:15–2:15 | Decompose `EP-001` → stories with citations; **click one citation live** |
| 2:15–3:00 | Criteria for file-upload story → open question on size limit |
| 3:00–3:30 | Generic story rejected by guard → regenerated |
| 3:30–4:00 | DoR blocks BL-012 with specific reason |
| 4:00–4:45 | Priority scores with visible arithmetic + dependency constraint |
| 4:45–5:30 | Approval queue: pending write blocked → approve → tracker record (AI-drafted, NOT_READY) → no duplicate |
| 5:30–6:00 | Overlap flag on BL-006 (if built) |
| 6:00–7:00 | `python -m eval.run` output + **"Weakest part is X; with one more week I'd Y"** |

---

## Golden Test Cases → Implementation Map (Tab 07)

| Case | Primary capability | When to implement |
|------|-------------------|-------------------|
| TC-01 Citation resolution | O1 + O6 | Day 1 |
| TC-02 Open-question recall | O3 | Day 1 |
| TC-03 Generic story rate | O8 | Day 2 |
| TC-04 Decomposition coverage | O2 | Day 2 |
| TC-05 Readiness accuracy | O4 | Day 2 |
| TC-06 Priority reproducibility | O5 | Day 3 |
| TC-07 Overlap detection | O7 | Day 3 |
| TC-08 Thin epic | O2 | Day 2 |
| TC-09 Approval + status floor | O9 | Day 3 |
| TC-10 Glossary consistency | O6 + O3 | Day 2 |

---

## Git Commit Strategy (Tab 04, Tab 10)

**Minimum 12 meaningful commits across 4 days:**

```
Day 1: chore: initialize | feat: sample data | feat: O1 context | feat: O6 citations | feat: O3 criteria
Day 2: feat: O2 decompose | feat: O8 generic guard | feat: O4 DoR | test: golden cases 1-2-5-8
Day 3: feat: O9 approval gate | feat: O5 prioritization | feat: O7 overlap | feat: streamlit UI
Day 4: test: complete eval harness | fix: eval failures | docs: architecture + decision log | docs: README
```

Never: one giant final commit.

---

## Optional Recommendations (choose based on time)

### If ahead of schedule (Day 3 evening free)

| Priority | Add | Golden case / rubric boost |
|----------|-----|---------------------------|
| 1 | **O10** stakeholder synthesis + consent refusal | Shows SHOULD capability |
| 2 | **Contradiction detection** (brief vs BL-014) | Stretch idea Tab 07 |
| 3 | **Claim-level grounding** UI — click claim → source highlight | Demo wow factor |
| 4 | **Prompt version regression** in eval | Exceptional band insight |

### If behind schedule (Day 3 afternoon)

| Cut | Impact | Mitigation |
|-----|--------|------------|
| O7 overlap | Lose Golden Case 7, partial SHOULD | Mark "Not built", note in decision log |
| O8 anti-generic | Lose Golden Case 3 metric | Basic pattern list still in prompt; mark Partial |
| Streamlit polish | None — UI not scored | Keep Approval Queue only |
| O10 | None — SHOULD | Mark "Not built" |

### LLM cost management (Tab 03)

- Cache LLM responses during dev (`data/llm_cache/`)
- Use smaller model for eval runs
- Document rate-limit workaround in README if hit

---

## Submission Checklist (Tab 09 — verify Day 4)

- [ ] Public git repo with incremental commits
- [ ] README with honest status table
- [ ] Setup: install + seed + run (≤5 steps)
- [ ] `.env.example` with exact model version
- [ ] `docs/architecture.md` with approval gate diagram
- [ ] Adapter interfaces + mock implementations
- [ ] `eval/run.py` + committed `eval/results.json`
- [ ] `docs/decision-log.md`
- [ ] 5–10 min screen recording
- [ ] Sample data in repo (FlowDesk complete set)
- [ ] AI coding assistance declared in README

---

## What Will Differentiate You (Tab 08 band 5 insights)

1. **Claim-level citation validation** — not just "does PB-04.2 exist?" but "does it support this claim?"
2. **Open questions as required schema field** — model cannot omit uncertainty
3. **Status floor enforced in write path** — LLM never controls READY status
4. **Eval-driven development** — golden cases as executable requirements from Day 2
5. **Honest README** — Partial/Not built clearly marked (protects from auto-fail #1)
6. **Self-awareness in demo** — name weakest part unprompted (Rubric #8, #9)

---

## Pre-Implementation Checklist

Before writing application code, lock these **artifacts** in order:

1. **Pydantic schemas** — `StoryDraft`, `AcceptanceCriteriaDraft`, `Citation`, `DoRVerdict`, `Draft`
2. **Sample data files** — FlowDesk brief with all gaps planted
3. **Adapter protocols** — `Tracker`, `DocumentStore`
4. **`config/readiness.yaml`** + **`config/generic_guard.json`**
5. **`eval/golden_cases.json`** — write tests before full implementation

This prevents the most common failure mode (Tab 10): *building an LLM demo first and retrofitting grounding, approval, and evaluation later.*

---

## Next Step

When ready to start implementation, begin with the repo scaffold + FlowDesk sample data + database schema — in that order, not with the LLM.
