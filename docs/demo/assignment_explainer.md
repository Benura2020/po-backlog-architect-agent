# 🧠 Assignment Explainer — What to Say in the Demo

---

## 🎯 PART 1 — "Can you briefly explain what this assignment is about?"

**What to say (in your own words):**

> *"The assignment was to build an AI-powered Product Owner assistant — called the PO Backlog Architect Agent — for a fictional software company called FlowDesk.*
>
> *FlowDesk is basically a service desk / ticketing system — like a company's internal IT helpdesk tool.*
>
> *The problem is this: when you use AI to write software requirements (called user stories), the AI tends to make things up, write vague useless stories, or push unreviewed content directly into the project tracker like Jira. That's dangerous.*
>
> *So the assignment was to build an agent that helps a Product Owner (PO) create, validate, and govern backlog items — but with proper guardrails so the AI cannot do anything unsafe on its own.*
>
> *The core idea is: the AI proposes, the human approves, and the system enforces that with real code — not just a warning message."*

---

## 🧩 PART 2 — "What are the sections in the UI and what do they do?"

There are **7 tabs** (sections) in the dashboard + **1 evaluation tab**. Here's what each one does in plain English:

---

### 📌 Tab 1 — Context Search (O1)
**What is it?**
This is where the system reads and understands the **FlowDesk Product Brief** — the document that describes what FlowDesk is supposed to do.

**What actually happens here?**
- The product brief is split into **15 numbered sections** (PB-01 to PB-15) — like chapters.
- These sections are loaded into a **search engine** built on SQLite (a simple database).
- You can type a keyword like `"file upload"` and it returns the exact sections that mention it.
- Each result shows the section ID (e.g. `PB-04.1`) and the actual text.

**Why does this matter?**
Every user story the AI writes later must point back to one of these sections as proof. If it can't cite a real section, the claim is rejected. This prevents the AI from making things up.

**Simple analogy:** It's like the AI must show its homework — it can't write a requirement without showing which page of the spec it came from.

---

### 📌 Tab 2 — Epic Decomposer (O2)
**What is it?**
An **Epic** is a big, high-level feature (like "Document Management"). This tab breaks a big epic down into smaller, actionable **user stories**.

**What actually happens here?**
- You pick an Epic from the dropdown (e.g. EP-001 or EP-002).
- The AI reads the product brief sections related to that epic.
- It generates multiple smaller user stories in the format: *"As a [role], I want [action] so that [benefit]."*
- It also surfaces **open questions** — things that are unclear or missing in the specification.

**The interesting edge case:**
- **EP-001** (Document Management) is a well-specified epic → AI generates complete stories.
- **EP-002** (Approval Automation) is a thin/vague epic → Instead of making things up, the agent generates **more open questions than stories** and raises a `thin_epic_flag = True`. It's basically saying *"I don't have enough information to write this properly."*

**Why does this matter?**
This stops the AI from hallucinating stories for requirements that don't exist yet.

---

### 📌 Tab 3 — Criteria Generator + Anti-Generic Guard (O3 / O6 / O8)
**What is it?**
This is the most feature-rich tab. It does two things:
1. **Generates acceptance criteria** (the pass/fail conditions for a story)
2. **Checks if a story is vague or generic** and either flags or rewrites it

**Part A — Acceptance Criteria:**
- You select a backlog story.
- The AI generates **Given / When / Then** scenarios — these are the test conditions for the story.
- Each claim in the criteria is linked back to a specific product brief section (like `PB-04.2`) as a citation.
- If a claim is made that has no backing in the product brief, it's flagged as **unsupported**.

**Part B — Anti-Generic Guard (3 Layers):**
This is a system that detects and blocks vague user stories. It runs 3 checks:

| Layer | What it checks | Example |
|---|---|---|
| Layer 1 | Is the text in a list of known bad phrases? | "manage data" → BLOCKED |
| Layer 2 | Does it use vague verbs with generic nouns? | "manage.*data" regex → BLOCKED |
| Layer 3 | Does it score well on 6 specificity dimensions? | Score 0/6 → GENERIC |

The **6 dimensions** scored in Layer 3 are:
- Does it have a role? (As a *[someone]*)
- Does it mention a specific domain object? (ticket, SLA, catalog)
- Does it use a concrete action verb? (filter, upload, approve)
- Does it have a measurable outcome?
- Does it use FlowDesk-specific terms?
- Does it have testable behavior (Given/When/Then)?

If the story fails, it is **automatically rewritten** into a domain-specific, testable story.

**Demo moment:** Type `"Manage my data efficiently"` → watch it score 0/6 → see the rewrite.

---

### 📌 Tab 4 — Definition of Ready (DoR) Gate (O4)
**What is it?**
Before a story can be worked on in a sprint, it must pass a **readiness check** — like a quality gate.

**What actually happens here?**
- You select a story from the backlog.
- The system checks it against **6 rules** defined in the `config/readiness.yaml` file.
- Each rule is checked: PASS or FAIL.
- Final verdict: **READY** (story can proceed) or **BLOCKED** (with specific reasons why).

**The 6 rules are:**
1. Does it follow the "As a... I want... So that..." format?
2. Does it have acceptance criteria (Given/When/Then)?
3. Are all citations pointing to real sections in the product brief?
4. Are all dependency stories already in READY status?
5. Are there no unresolved open questions?
6. Is it domain-specific (passes the anti-generic check)?

**Demo moment:** Select `BL-003` → BLOCKED. Select `BL-005` → READY. Show the difference.

**Why does this matter?**
Teams can change these rules in the YAML file. It's configurable — if your team has different standards, you just edit the file.

---

### 📌 Tab 5 — Prioritization Engine (O5)
**What is it?**
This ranks all the backlog stories in order of importance using a **mathematical formula** — not an AI guess.

**What actually happens here?**
- You click "Run Prioritization Engine."
- Every story in the backlog gets a **priority score** calculated by this formula:

```
Score = (Business Value × 0.40)
      + (Urgency × 0.25)
      + (Risk Reduction × 0.20)
      + (Strategic Alignment × 0.15)
      × Readiness Factor
      × (1 - 0.10 × Dependency Penalty)
```

- Stories are then **sorted by score** (highest first).
- Stories that have unresolved dependencies are pushed down — they can't go into a sprint before their blockers are done.
- You can expand any story and see the exact numbers behind the score.

**Why does this matter?**
The score is 100% deterministic — the same inputs always produce the same score. No AI randomness. No subjective guessing.

---

### 📌 Tab 6 — Overlap Detector (O7)
**What is it?**
This checks if a new story is too similar to something already in the backlog — to prevent duplicate work.

**What actually happens here?**
- You select a candidate story.
- The system compares it against all existing backlog items using **word similarity matching** (Jaccard similarity).
- It classifies the relationship as one of:
  - **DUPLICATE** — exactly the same thing
  - **SUBSET** — your story is a smaller part of an existing one
  - **SUPERSET** — your story covers more than an existing one
  - **ADJACENT** — related but different
  - **NONE** — no overlap
- It also shows a confidence score and a recommended action.

**Why does this matter?**
Prevents two teams from building the same feature without knowing about each other.

---

### 📌 Tab 7 — Approval Queue & Write Gate (O9)
**What is it?**
This is the most important governance section. It controls whether an AI-generated story can be written to an external tracker (like Jira).

**What actually happens here — step by step:**

**Step 1:** When a story draft is created anywhere in the system, it enters the approval queue with status `PENDING`.

**Step 2:** If someone clicks **"Write to Tracker"** on a PENDING draft:
- The system returns `HTTP 403 Forbidden` — a hard block.
- Error message: *"Draft must be APPROVED before writing to tracker."*
- This is enforced in Python code — it cannot be bypassed.

**Step 3:** A human PO clicks **"Approve Draft."**
- Status changes from `PENDING` to `APPROVED`.
- An audit log entry is created with who approved it and when.

**Step 4:** Now click **"Write to Tracker"** → `HTTP 200 OK`
- The story is written to MockTracker.
- **Status is forcibly set to `NOT_READY`** — even if the AI said READY.
- **Tag `AI-drafted` is added** — so everyone knows this came from AI.

**Why does this matter?**
The AI can never push a story to READY status. It is physically impossible in this system. The service layer blocks it — it's not a warning, it's a wall.

---

### 📌 Tab 8 — Evaluation Dashboard (Bonus / Stretch)
**What is it?**
This shows the results of running the automated evaluation suite against the system.

**What actually happens here?**
- **10 Golden Test Cases** — predefined scenarios that test every capability. All 10 pass.
- **Mock Provider results** — run offline, deterministic, instant.
- **Groq Live LLM results** — run against the real AI model, avg 1.45s latency.
- **7 Adversarial Probes** — attack scenarios designed to break the system (hallucinations, prompt injection, generic guard evasion, etc.). All 7 blocked.

---

## 🔑 PART 3 — If They Ask: "What is the overall flow from start to finish?"

**Say this:**

> *"A PO opens the dashboard. They search for relevant product brief sections in Tab 1. They pick an epic in Tab 2 and decompose it into user stories. Tab 3 generates acceptance criteria for each story and checks that each one is specific and grounded in the spec. Tab 4 runs the Definition of Ready check — the story either passes all 6 rules or it's blocked with reasons. Tab 5 ranks all ready stories by a formula score. Tab 6 checks for duplicates. Then in Tab 7, the PO reviews the draft, approves it, and only then can it be written to the external tracker — locked at NOT_READY and tagged as AI-drafted."*

---

## ⚡ PART 4 — Key Numbers to Remember

| What | Number |
|---|---|
| Product brief sections | 15 (PB-01 to PB-15) |
| Definition of Ready rules | 6 rules (in readiness.yaml) |
| Anti-Generic Guard layers | 3 layers |
| Specificity scoring dimensions | 6 dimensions |
| Backlog items in sample data | 20 (BL-001 to BL-020) |
| Epics in sample data | 2 (EP-001 detailed, EP-002 thin) |
| Automated tests | 24/24 passing |
| Golden test cases | 10/10 passing |
| Adversarial probes | 7/7 passing |
| Capabilities built | 9 out of 12 (O1-O9, skipped O10-O12) |
