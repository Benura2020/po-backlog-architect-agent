# Edge Cases & Failure Handling — PO Backlog Architect Agent

This document records the two primary edge cases / failure modes demonstrated in the recorded walkthrough and proven by the evaluation suite.

---

## Edge Case A: Unapproved Write Blocked (HTTP 403 Forbidden)

**Scenario**: An external system or user attempts to write a `PENDING` draft directly to MockTracker without human approval.

**Demonstrated in**: Tab 7 (Approval Queue) — Walkthrough video timestamp ~6:30

### What Happens

1. A draft item is created in `PENDING` state in the approval queue.
2. User clicks **"Write to MockTracker"** on the `PENDING` draft.
3. `ApprovalService.write_draft_to_tracker()` checks `draft.status`:

```python
# app/services/approval_service.py — the structural gate
if draft.status != ApprovalStatus.APPROVED:
    raise ApprovalRequiredError(
        f"Draft {draft_id} must be APPROVED before writing to tracker "
        f"(current status: {draft.status.value})"
    )
```

4. **Result**: Service layer raises `ApprovalRequiredError`. FastAPI returns **`HTTP 403 Forbidden`**.

### UI Evidence

![Tab 7: Approval Queue — PENDING draft write blocked](images/tab7_approval_queue.png)

The Streamlit dashboard shows the red error banner:
```
❌ WRITE BLOCKED BY SERVICE LAYER: Draft must be APPROVED (HTTP 403 Forbidden)
```

### Automated Test Evidence

```
tests/test_api_integration.py::TestApprovalGateHTTP::test_pending_draft_write_returns_403  PASSED
tests/test_api_integration.py::TestApprovalGateHTTP::test_rejected_draft_write_returns_403 PASSED
tests/test_e2e_pipeline.py::TestE2E02ApprovalBypass::test_pending_write_always_blocked       PASSED
```

**Adversarial probe ADV-06** also verifies that even when the LLM output payload contains `"status": "READY"`, the service layer overrides it to `NOT_READY`.

---

## Edge Case B: Generic Story Detected, Flagged & Auto-Rewritten

**Scenario**: A user inputs a vague, non-specific story like `"Manage my data efficiently"`.

**Demonstrated in**: Tab 3 (Criteria Generator / Anti-Generic Guard) — Walkthrough video timestamp ~4:00

### What Happens

The **3-Layer Anti-Generic Guard** (`app/services/generic_guard_service.py`) runs automatically:

**Layer 1 — Exact Phrase Match**:
```
Input: "Manage my data efficiently"
Forbidden phrase matched: "manage data"
→ FAIL: Exact generic phrase detected
```

**Layer 2 — Vague Verb Regex**:
```
Pattern: r'\b(manage|handle|deal with|process)\b.*\b(data|information|content)\b'
→ FAIL: Vague verb + generic object pattern matched
```

**Layer 3 — 6-Dimension Specificity Scoring**:
```
role_identified:          ❌ 0  (no "As a [role]" format)
concrete_domain_object:   ❌ 0  (no specific domain noun)
concrete_action_verb:     ❌ 0  (vague "manage" verb)
measurable_outcome:       ❌ 0  (no measurable benefit)
distinct_domain_terms:    ❌ 0  (no FlowDesk domain terms)
testable_behavior:        ❌ 0  (no Given/When/Then)
─────────────────────────────
Total score: 0/6 → Classification: GENERIC (BLOCKED)
```

**Auto-Rewrite Output**:
```
As a FlowDesk service requester, I want to filter and search submitted
service requests by status, category, and date range so that I can
quickly locate pending approvals and track resolution progress.
```

### UI Evidence

![Tab 3: Criteria Generator — Anti-Generic Guard in action](images/tab3_criteria_generator.png)

### Automated Test Evidence

```
tests/test_e2e_pipeline.py::TestE2E05GenericStoryBlocked::test_generic_story_detected_3_layers  PASSED
tests/test_e2e_pipeline.py::TestE2E05GenericStoryBlocked::test_generic_story_rewritten           PASSED
eval/results_adversarial.json → ADV-02: PASS (Generic Story Rewrite Evasion)
eval/results_adversarial.json → ADV-03: PASS (Missing Actor Detection)
```

---

## Edge Case C: Hallucinated Numeric Requirement Rejected

**Scenario**: An LLM hallucinates a "50 MB file upload limit" that does not appear anywhere in the product brief.

**Demonstrated in**: Adversarial probe ADV-01 (`eval/adversarial_run.py`)

### What Happens

`CitationService.validate_citations()` checks each claim against the actual text of section `PB-04.2`:

```python
# The section PB-04.2 text contains no numeric MB limit
claim = "File uploads must not exceed 50 MB"
section_text = context_sections["PB-04.2"]  # No "50 MB" in text
→ citation_support = False
→ Added to unsupported_claims[]
```

**Result**: Claim is placed in `unsupported_claims[]` and never silently accepted as valid context. The evaluation returns `citation_support=False` and the story is flagged.

### Automated Test Evidence

```
tests/test_e2e_pipeline.py::TestE2E04UnsupportedClaim::test_hallucinated_size_limit_not_supported  PASSED
eval/results_adversarial.json → ADV-01: PASS (Hallucinated Numeric Requirement)
```

---

## Edge Case D: Thin Epic Surfaces Open Questions (Not Stories)

**Scenario**: A thin, underspecified epic (`EP-002: Approval Automation`) is decomposed.

**Demonstrated in**: Tab 2 (Epic Decomposer) — select EP-002

### What Happens

`DecompositionAgent` detects the epic has insufficient detail (`thin_epic_flag = True`) and generates more open questions than stories:

```
questions generated: 3
stories generated:   1
thin_epic_flag:      True
```

This prevents the agent from fabricating stories for underspecified requirements.

### Automated Test Evidence

```
tests/test_e2e_pipeline.py::TestE2E03ThinEpicDorBlocked::test_thin_epic_questions_exceed_stories  PASSED
eval/results.json → TC-08 (Thin Epic Behaviour): PASS
```

---

## Summary

| # | Edge Case | Layer | HTTP Code | Test Evidence |
|---|-----------|-------|-----------|---------------|
| A | Unapproved write blocked | Service layer (Python) | `HTTP 403` | `test_pending_draft_write_returns_403`, `ADV-06` |
| B | Generic story detected & rewritten | GenericGuardService | N/A (UI flag) | `E2E-05`, `ADV-02`, `ADV-03` |
| C | Hallucinated number rejected | CitationService | N/A (flag) | `E2E-04`, `ADV-01` |
| D | Thin epic surfaces questions | DecompositionAgent | N/A (flag) | `E2E-03`, `TC-08` |
