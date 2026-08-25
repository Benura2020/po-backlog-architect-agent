# Architecture Decision Log (ADR) — PO Backlog Architect Agent

**Project**: PO Backlog Architect Agent (FlowDesk)  
**Status**: Approved & Verified  

---

### ADR-001: FastAPI + Python Async Backend Architecture
- **Context**: Need a performant, lightweight REST API framework for AI PO backlog operations with high developer productivity and automatic OpenAPI documentation.
- **Decision**: Use FastAPI with Pydantic domain models.
- **Alternatives Considered**: Flask (lacks native async/OpenAPI schemas), Django (overly monolithic for focused agent services).
- **Rationale**: FastAPI provides instant OpenAPI docs (`/docs`), strong typing with Pydantic, and low overhead.
- **Trade-off**: Requires careful dependency injection for session scope management.

---

### ADR-002: SQLite Relational Persistence
- **Context**: Need local database persistence for backlog items, approval drafts, audit logs, and FTS5 context indexing without complex external database cluster dependencies.
- **Decision**: Use SQLite with SQLAlchemy ORM and `StaticPool` for multi-threaded test client support.
- **Alternatives Considered**: PostgreSQL (requires local server installation/Docker setup), In-memory dictionary (lacks relational integrity and persistence).
- **Rationale**: SQLite provides zero-infrastructure, zero-config relational persistence and FTS5 full-text indexing directly in a single local file (`flowdesk.db`).
- **Trade-off**: Single-writer lock concurrency limit; easily upgraded to PostgreSQL behind SQLAlchemy ORM abstraction if required.

---

### ADR-003: SQLite FTS5 Section Indexing vs Vector Store
- **Context**: Product context documents (`product_brief.md`) require section-level citations (`PB-01`...`PB-15`).
- **Decision**: Use SQLite FTS5 full-text index for section-level Markdown indexing.
- **Alternatives Considered**: ChromaDB / Pinecone vector stores.
- **Rationale**: Product brief context is structured and compact. Section-level FTS5 keyword indexing delivers 100% deterministic citation references (`PB-04.1`) without embedding generation overhead or vector store infrastructure.
- **Trade-off**: Requires structured Markdown heading conventions for section splitting.

---

### ADR-004: LLMProvider Abstract Protocol & Adapter Pattern
- **Context**: Need to decouple domain logic from specific LLM vendors (Groq, OpenAI, Ollama) and support offline deterministic testing.
- **Decision**: Implement `LLMProvider` abstract protocol interface with `GroqProvider` (`qwen/qwen3.6-27b`) and `MockProvider`.
- **Alternatives Considered**: Direct LangChain / LlamaIndex dependency.
- **Rationale**: Avoids heavy framework bloat. Provides clean retry loops, custom Pydantic schema validation, and instant fallback when API keys are unconfigured.
- **Trade-off**: Manual implementation of Pydantic JSON retry loops (handled in `groq_provider.py`).

---

### ADR-005: MockProvider Baseline for Deterministic CI Evaluation
- **Context**: Need instant, 100% reproducible regression testing for automated test suites without network latency, API costs, or LLM flakiness.
- **Decision**: Include `MockProvider` alongside `GroqProvider`.
- **Alternatives Considered**: Mocking HTTP calls at `httpx` level.
- **Rationale**: `MockProvider` enables 0.05-second test suite execution and guaranteed 10/10 deterministic regression baselines.
- **Trade-off**: Mock output is fixed; live LLM capabilities are validated separately via `--provider groq`.

---

### ADR-006: Service-Layer Approval Gate & State Machine
- **Context**: Prevent unapproved AI-generated story drafts from being written to external issue trackers (Jira/MockTracker).
- **Decision**: Enforce draft state machine (`PENDING` → `APPROVED` / `REJECTED` → `WRITTEN`) inside `ApprovalService` in Python code.
- **Alternatives Considered**: Prompting the LLM to only write when approved.
- **Rationale**: Prompt instructions can be bypassed or prompt-injected. Service-layer code enforcement blocks unapproved writes with `HTTP 403 Forbidden` regardless of caller intent.
- **Trade-off**: Requires explicit human approval step before tracker write.

---

### ADR-007: Immutable NOT_READY Status Floor & AI-Drafted Tagging
- **Context**: Ensure AI-generated backlog items never enter tracker as `READY` for sprint allocation without human PO review.
- **Decision**: `ApprovalService` forcibly overrides item status to `NOT_READY` and appends tag `"AI-drafted"` when writing to tracker.
- **Alternatives Considered**: Trusting LLM output payload status field.
- **Rationale**: Eliminates premature sprint commitment risk. Demonstrates structural governance over probabilistic AI output.
- **Trade-off**: Human PO must manually update status to `READY` in tracker after review.

---

### ADR-008: Deliberate Scope Cut of Secondary Capabilities (O10–O12)
- **Context**: Challenge specification listed secondary capabilities (Stakeholder Synthesis O10, Batch Criteria O11, Release Notes O12).
- **Decision**: Scope cut O10–O12 to focus 100% engineering depth on core architecture, 3-layer anti-generic guard, DoR governance, and evaluation infrastructure.
- **Rationale**: Prioritizes production-grade governance and evaluation quality over surface-level feature quantity.
- **Trade-off**: O10–O12 documented as future work in architecture specification.
