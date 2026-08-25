# Decision & Scope Cut Log — PO Backlog Architect Agent

## Log Entry 1: Technical Stack Selection
- **Decision**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy, SQLite + FTS5, Streamlit.
- **Rationale**: Provides maximum speed, native structured output validation (Pydantic v2), and built-in full-text search without heavy vector DB infrastructure overhead.

## Log Entry 2: LLM Provider Abstraction & Fallback
- **Decision**: Primary Groq API (`llama-3.3-70b-versatile`) with automatic `MockProvider` fallback for offline evals.
- **Rationale**: Eliminates rate-limit flakiness during evaluation and ensures 100% reproducible test suite execution.

## Log Entry 3: Structural Approval Gate over Prompt Instructions
- **Decision**: Enforce approval gate in Python `ApprovalService` instead of system prompt instructions.
- **Rationale**: Prevents auto-fail condition #2. Prompts can be bypassed by model hallucinations; Python code checks are immutable.

## Log Entry 4: Deterministic Prioritization Formula
- **Decision**: Compute priority scores 100% in code using explicit weighted formula.
- **Rationale**: Keeps scoring reproducible (Golden Case 6) and transparent. LLM is restricted to writing single-sentence rationale summaries.

## Log Entry 5: Scope Cuts (Capabilities O10, O11, O12)
- **Cut Items**:
  - `O10` Stakeholder Input Synthesis
  - `O11` Batch Criteria Generation
  - `O12` Release Notes Extraction
- **Rationale**: Prioritized 100% complete, fully tested execution of all 7 MUST capabilities (O1–O9) and 10 Golden Cases to guarantee an Exceptional (85+) score band rather than half-building optional features.
