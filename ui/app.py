import os
import sys
import json

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Remove colliding 'app' module if registered as ui/app.py by Streamlit runner
if "app" in sys.modules and getattr(sys.modules["app"], "__file__", "").endswith("app.py"):
    del sys.modules["app"]

import streamlit as st
from sqlalchemy.orm import Session

from app.db.database import Base, engine, SessionLocal
from app.models.models import BacklogItemModel, DraftModel, ApprovalLogModel, WriteLogModel
from app.services.context_service import ContextService
from app.services.citation_service import CitationService
from app.agents.criteria_agent import CriteriaAgent
from app.agents.decomposition_agent import DecompositionAgent
from app.services.readiness_service import ReadinessService
from app.services.approval_service import ApprovalService, ApprovalRequiredError, AlreadyWrittenError
from app.services.prioritization_service import PrioritizationService
from app.services.overlap_service import OverlapService
from app.llm.groq_provider import GroqProvider
from app.llm.mock_provider import MockProvider
from eval.run import run_evaluation

st.set_page_config(
    page_title="FlowDesk — PO Backlog Architect Agent",
    page_icon="🤖",
    layout="wide"
)

# Initialize DB tables
Base.metadata.create_all(bind=engine)


@st.cache_resource
def get_llm():
    provider = os.getenv("LLM_PROVIDER", "groq")
    if provider.lower() == "groq" and os.getenv("GROQ_API_KEY"):
        return GroqProvider()
    return MockProvider()


def get_db_session():
    return SessionLocal()


# Title & Header Banner
st.title("🤖 FlowDesk — PO Backlog Architect Agent")
st.caption("AI-powered Product Owner Assistant — Grounded Criteria, Human-Gated Approvals & Measured Quality")

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")
provider_option = st.sidebar.selectbox("LLM Provider", ["Groq (qwen/qwen3.6-27b)", "Mock Provider (Offline Deterministic)"])
use_mock = "Mock" in provider_option

st.sidebar.divider()
st.sidebar.markdown("**Auto-Fail Safeguards Active:**")
st.sidebar.markdown("✅ Structural Approval Gate (Service Layer)")
st.sidebar.markdown("✅ Status Floor Forced at `NOT_READY`")
st.sidebar.markdown("✅ Claim-Level Citation Verification")

# Main Navigation Tabs
tabs = st.tabs([
    "1. Context Search (O1)",
    "2. Epic Decomposer (O2)",
    "3. Criteria Generator (O3/O6)",
    "4. Readiness Gate (O4)",
    "5. Prioritization (O5)",
    "6. Overlap Detector (O7)",
    "7. Approval Queue (O9)",
    "8. Eval Dashboard"
])

db = get_db_session()
llm = MockProvider() if use_mock else get_llm()

# TAB 1: CONTEXT SEARCH (O1)
with tabs[0]:
    st.header("🔍 Context Indexing & Addressable Search (O1)")
    st.write("Browse and query addressable sections (`PB-01` … `PB-15`) from `product_brief.md` stored in SQLite FTS5.")

    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("Search Product Brief Context", value="file upload")
    with col2:
        st.write("")
        st.write("")
        do_search = st.button("Search Context", use_container_width=True)

    context_svc = ContextService(db)
    if search_query:
        results = context_svc.search_context(search_query, limit=5)
        st.subheader(f"Found {len(results)} Addressable Sections")
        for res in results:
            with st.expander(f"📌 [{res['ref']}] {res['title']}"):
                st.markdown(res['content'])
                st.caption(f"Source Document: {res['document_name']}")

# TAB 2: EPIC DECOMPOSER (O2)
with tabs[1]:
    st.header("🧩 Epic Decomposition (O2)")
    st.write("Decompose epics into grounded user stories. Thin epics surface questions over invented features.")

    epics_file = os.path.join(os.getenv("DATA_DIR", "./data"), "epics.json")
    if os.path.exists(epics_file):
        with open(epics_file, "r") as f:
            epics_data = json.load(f)

        selected_epic_idx = st.selectbox("Select Seed Epic", range(len(epics_data)), format_func=lambda i: f"{epics_data[i]['id']}: {epics_data[i]['title']}")
        selected_epic = epics_data[selected_epic_idx]

        st.info(f"**Description**: {selected_epic['description']}\n\n**Is Thin Epic**: {selected_epic.get('is_thin', False)}")

        if st.button("Decompose Epic"):
            agent = DecompositionAgent(llm, db)
            res = agent.decompose_epic(
                epic_id=selected_epic["id"],
                epic_title=selected_epic["title"],
                epic_description=selected_epic["description"],
                is_thin=selected_epic.get("is_thin", False)
            )

            if res.thin_epic_flag:
                st.warning("⚠️ THIN EPIC DETECTED: Agent produced open questions rather than inventing missing specifications.")

            st.subheader("Extracted Stories")
            for s in res.stories:
                st.markdown(f"#### 📖 {s.title}")
                st.markdown(f"**Description**: {s.description}")
                st.markdown(f"**Rationale**: {s.rationale}")
                if s.citations:
                    st.caption(f"Citations: {[c.ref for c in s.citations]}")

            if res.open_questions:
                st.subheader("❓ Surfaced Open Questions")
                for q in res.open_questions:
                    st.error(f"**{q.question}**\n\n*Reason*: {q.reason}")

# TAB 3: CRITERIA GENERATOR (O3, O6)
with tabs[2]:
    st.header("✍️ Structured Acceptance Criteria & Planted Gaps (O3, O6)")
    st.write("Generate Given/When/Then acceptance criteria with mandatory open questions for planted silences.")

    story_title = st.text_input("Story Title", value="Upload Supporting Documents to Request")
    story_desc = st.text_area("Story Description", value="As a Requester, I want to attach PDF and image files to my service ticket so fulfillment agents have necessary context.")

    if st.button("Generate Acceptance Criteria"):
        agent = CriteriaAgent(llm, db)
        draft = agent.generate_criteria("BL-006", story_title, story_desc)

        st.success("Criteria generated successfully!")

        st.subheader("Given / When / Then Criteria")
        for c in draft.happy_path:
            st.markdown(f"- **Given** {c.given}  \n  **When** {c.when}  \n  **Then** {c.then}")

        if draft.open_questions:
            st.subheader("🚨 Planted Gap Open Questions (Fabrication Probe)")
            for q in draft.open_questions:
                st.warning(f"❓ **{q.question}**  \n*Missing Concept*: `{q.missing_concept}`  \n*Reason*: {q.reason}")

        if draft.citations:
            st.subheader("🔗 Addressable Section Citations")
            for cit in draft.citations:
                st.markdown(f"-[{cit.ref}] Source: {cit.source}")

# TAB 4: READINESS GATE (O4)
with tabs[3]:
    st.header("🚦 Definition of Ready (DoR) Gate (O4)")
    st.write("Check stories against configurable `readiness.yaml` rules. Log human overrides.")

    items = db.query(BacklogItemModel).all()
    item_options = [f"{i.id}: {i.title}" for i in items]
    sel_item = st.selectbox("Select Backlog Story", item_options)

    if sel_item:
        item_id = sel_item.split(":")[0]
        db_item = db.query(BacklogItemModel).filter(BacklogItemModel.id == item_id).first()

        readiness_svc = ReadinessService(db)
        verdict = readiness_svc.evaluate_story(
            story_id=db_item.id,
            title=db_item.title,
            description=db_item.description,
            acceptance_criteria=db_item.acceptance_criteria,
            citations=json.loads(db_item.citations or "[]")
        )

        if verdict.status == "READY":
            st.success(f"VERDICT: READY ✅")
        else:
            st.error(f"VERDICT: BLOCKED ❌")
            st.markdown("**Blocking Reasons:**")
            for r in verdict.blocking_reasons:
                st.write(f"- ❌ {r}")

        st.subheader("DoR Checklist Verification")
        for check in verdict.checks:
            icon = "✅" if check.passed else "❌"
            st.write(f"{icon} **{check.rule_name}**: {check.details}")

        st.divider()
        st.subheader("Human Override Log")
        override_actor = st.text_input("Override Actor Name", value="Human Lead PO")
        override_reason = st.text_area("Override Reason", value="Approved for sprint spike despite missing criteria.")
        if st.button("Record Human Override"):
            res = readiness_svc.record_human_override(db_item.id, override_actor, override_reason)
            st.warning(f"Override Recorded! Story status set to READY (Human Overridden).")

# TAB 5: PRIORITIZATION (O5)
with tabs[4]:
    st.header("📊 Deterministic Prioritization Engine (O5)")
    st.write("100% code arithmetic scoring formula with visible weights and topological dependency sorting.")

    st.latex(r"\text{Base} = 0.40 \cdot \text{BV} + 0.25 \cdot \text{Urg} + 0.20 \cdot \text{Risk} + 0.15 \cdot \text{Align}")
    st.latex(r"\text{Final} = \text{Base} \cdot \text{ReadinessFactor} \cdot (1 - 0.10 \cdot \text{DependencyPenalty})")

    prio_svc = PrioritizationService(db, llm)
    prioritized = prio_svc.prioritize_backlog()

    st.subheader("Prioritized Backlog Ranking")
    for idx, p in enumerate(prioritized):
        status_badge = "✅ READY" if p.readiness_factor > 0 else "🛑 BLOCKED (Score = 0)"
        st.markdown(f"### #{idx+1} Story {p.story_id} — Score: `{p.computed_score}` ({status_badge})")
        st.caption(f"BV: {p.business_value} | Urg: {p.urgency} | Risk: {p.risk_reduction} | Align: {p.strategic_alignment} | Readiness: {p.readiness_factor} | Dep Penalty: {p.dependency_penalty}")
        st.write(f"*Rationale*: {p.rationale}")

# TAB 6: OVERLAP DETECTOR (O7)
with tabs[5]:
    st.header("🔄 Backlog Overlap Detection (O7)")
    st.write("Detect relationship types (`DUPLICATE`, `SUBSET`, `SUPERSET`, `ADJACENT`) between new stories and existing backlog.")

    ov_title = st.text_input("New Story Title", value="Upload Supporting Documents to Request")
    ov_desc = st.text_area("New Story Description", value="As a Requester, I want to attach PDF files to my ticket")

    if st.button("Check Backlog Overlap"):
        from app.schemas.domain import StoryDraft
        dummy_story = StoryDraft(title=ov_title, description=ov_desc, rationale="")
        overlap_svc = OverlapService(db)
        overlaps = overlap_svc.check_overlap(dummy_story)

        if overlaps:
            for o in overlaps:
                st.warning(f"⚠️ **OVERLAP DETECTED** with `{o.existing_item_id}`")
                st.write(f"- **Relationship**: `{o.relationship_type.value}`")
                st.write(f"- **Recommendation**: {o.recommendation}")
                st.write(f"- **Confidence**: {o.confidence}")
        else:
            st.success("No overlapping items found in existing backlog.")

# TAB 7: APPROVAL QUEUE (O9 - CORE DEMO TAB)
with tabs[6]:
    st.header("🛡️ Approval Queue & Status Floor Gate (O9)")
    st.info("⚡ **Critical Assessment Demonstration**: External tracker writes are structurally blocked until a human approves the draft in code. Approved items are automatically tagged `AI-drafted` and locked at status `NOT_READY`.")

    approval_svc = ApprovalService(db)
    drafts = approval_svc.get_all_drafts()

    if not drafts:
        st.info("No drafts in queue. Generating sample draft...")
        approval_svc.create_draft("STORY", "Upload Supporting Documents", {"id": "ST-018", "title": "Upload Supporting Documents", "description": "Attach files"})
        drafts = approval_svc.get_all_drafts()

    st.subheader("Draft Queue Items")
    for d in drafts:
        with st.expander(f"📄 Draft: {d.title} (ID: {d.id}) — Status: **{d.status.value}**"):
            st.json(json.loads(d.payload_json))

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button(f"Approve {d.id}", key=f"app_{d.id}"):
                    approval_svc.approve_draft(d.id, "Human PO", "Approved in Streamlit UI")
                    st.rerun()
            with col_b:
                if st.button(f"Reject {d.id}", key=f"rej_{d.id}"):
                    approval_svc.reject_draft(d.id, "Human PO", "Rejected in Streamlit UI")
                    st.rerun()
            with col_c:
                if st.button(f"Write to MockTracker ({d.id})", key=f"wr_{d.id}"):
                    try:
                        record = approval_svc.write_draft_to_tracker(d.id)
                        st.success(f"✅ WRITTEN TO TRACKER! Record ID: `{record['id']}`, Tag: `{record['tags']}`, Status: `{record['status']}`")
                    except (ApprovalRequiredError, AlreadyWrittenError) as e:
                        st.error(f"❌ WRITE BLOCKED BY SERVICE LAYER: {e}")

# TAB 8: EVALUATION DASHBOARD
with tabs[7]:
    st.header("📈 Evaluation Harness & Golden Cases Dashboard")
    st.write("Run the automated evaluation harness (`python -m eval.run`) directly from the UI.")

    if st.button("Run Full Evaluation Suite"):
        with st.spinner("Executing 10 Golden Test Cases..."):
            eval_output = run_evaluation()

        st.success(f"Evaluation Complete! Pass Rate: {eval_output['pass_rate']*100:.1f}% ({eval_output['passed_cases']}/{eval_output['total_cases']})")

        st.subheader("Golden Case Results")
        for res in eval_output["results"]:
            badge = "✅ PASS" if res["passed"] else "❌ FAIL"
            st.write(f"**[{res['case_id']}] {res['name']}**: Target = `{res['target']}`, Actual = `{res['actual']}` -> {badge}")

db.close()
