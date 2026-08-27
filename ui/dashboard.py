import os
import sys
import json

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import streamlit as st
from sqlalchemy.orm import Session

from app.db.database import Base, engine, SessionLocal
from app.models.models import BacklogItemModel, DraftModel, ApprovalLogModel, WriteLogModel
from app.schemas.domain import DraftStatus
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

# TAB 3: CRITERIA GENERATOR & ANTI-GENERIC GUARD (O3, O6, O8)
with tabs[2]:
    st.header("✍️ Structured Acceptance Criteria & Planted Gaps (O3, O6)")
    st.write("Generate Given/When/Then acceptance criteria with mandatory open questions for planted silences.")

    items = db.query(BacklogItemModel).all()
    if not items:
        from app.seed import seed_database
        seed_database()
        items = db.query(BacklogItemModel).all()

    item_options_tab3 = ["Custom Story / Free Text Input"] + [f"{i.id}: {i.title}" for i in items]
    default_idx_tab3 = 0
    for idx, opt in enumerate(item_options_tab3):
        if "BL-006" in opt:
            default_idx_tab3 = idx
            break

    sel_story_tab3 = st.selectbox("Select Backlog Story to Populate (or edit custom text below)", item_options_tab3, index=default_idx_tab3, key="tab3_story_select")

    default_title = "Upload Supporting Documents to Request"
    default_desc = "As a Requester, I want to attach PDF and image files to my service ticket so fulfillment agents have necessary context."
    selected_story_id = "BL-006"

    if sel_story_tab3 != "Custom Story / Free Text Input":
        sel_id = sel_story_tab3.split(":")[0]
        selected_story_id = sel_id
        db_item = db.query(BacklogItemModel).filter(BacklogItemModel.id == sel_id).first()
        if db_item:
            default_title = db_item.title
            default_desc = db_item.description

    story_title = st.text_input("Story Title", value=default_title, key="tab3_title_input")
    story_desc = st.text_area("Story Description", value=default_desc, key="tab3_desc_input")

    if st.button("Generate Acceptance Criteria"):
        agent = CriteriaAgent(llm, db)
        draft = agent.generate_criteria(selected_story_id, story_title, story_desc)

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

    st.divider()
    st.header("🛡️ 3-Layer Anti-Generic Guard & Story Rewriter (O8)")
    st.write("Evaluate any story against the 3-Layer Anti-Generic Guard (Exact phrase match, Vague verb regex, Specificity scoring).")

    guard_title = st.text_input("Test Story Title for Specificity Check", value="Manage my data efficiently", key="guard_title_input")
    guard_desc = st.text_area("Test Story Description", value="As a user I want to manage my data efficiently so that I can work.", key="guard_desc_input")

    if st.button("Evaluate Specificity & Rewrite"):
        from app.services.generic_guard_service import GenericGuardService
        from app.schemas.domain import StoryDraft

        guard_service = GenericGuardService()
        sample_draft = StoryDraft(
            id="TEST-001",
            title=guard_title,
            description=guard_desc,
            rationale="Test item for specificity evaluation"
        )
        res = guard_service.evaluate(sample_draft)

        if res.is_generic:
            st.error(f"🚨 Flagged as **{res.specificity_label}** (Specificity Score: {res.specificity_score} / 6)")
        else:
            st.success(f"✅ Classified as **{res.specificity_label}** (Specificity Score: {res.specificity_score} / 6)")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Layer 1: Forbidden Phrases**")
            if res.matched_forbidden_phrases:
                for p in res.matched_forbidden_phrases:
                    st.error(f"Matched: `{p}`")
            else:
                st.info("None matched")

        with col2:
            st.markdown("**Layer 2: Vague Verbs/Patterns**")
            if res.matched_vague_patterns:
                for vp in res.matched_vague_patterns:
                    st.warning(f"Matched: `{vp}`")
            else:
                st.info("None matched")

        with col3:
            st.markdown("**Layer 3: Specificity Deductions**")
            if res.scoring_reasons:
                for r in res.scoring_reasons:
                    st.write(f"- {r}")
            else:
                st.info("Full specificity points")

        if res.is_generic:
            st.subheader("✨ Auto-Rewritten Domain Story")
            rewritten_list, _ = guard_service.filter_and_regenerate([sample_draft])
            rewritten = rewritten_list[0]
            st.success(f"**Rewritten Title**: {rewritten.title}")
            st.markdown(f"**Rewritten Description**: {rewritten.description}")

# TAB 4: READINESS GATE (O4)
with tabs[3]:
    st.header("🚦 Definition of Ready (DoR) Gate (O4)")
    st.write("Check stories against configurable `readiness.yaml` rules. Log human overrides.")

    items = db.query(BacklogItemModel).all()
    if len(items) < 5:
        from app.seed import seed_database
        seed_database()
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

    item_options_tab6 = ["Custom Story / Free Text Input"] + [f"{i.id}: {i.title}" for i in items]
    default_idx_tab6 = 0
    for idx, opt in enumerate(item_options_tab6):
        if "BL-006" in opt:
            default_idx_tab6 = idx
            break

    sel_story_tab6 = st.selectbox("Select Candidate Story to Populate (or edit custom text below)", item_options_tab6, index=default_idx_tab6, key="tab6_story_select")

    default_ov_title = "Upload Supporting Documents to Request"
    default_ov_desc = "As a Requester, I want to attach PDF files to my ticket"

    if sel_story_tab6 != "Custom Story / Free Text Input":
        sel_id = sel_story_tab6.split(":")[0]
        db_item = db.query(BacklogItemModel).filter(BacklogItemModel.id == sel_id).first()
        if db_item:
            default_ov_title = db_item.title
            default_ov_desc = db_item.description

    ov_title = st.text_input("New Story Title", value=default_ov_title, key="tab6_title_input")
    ov_desc = st.text_area("New Story Description", value=default_ov_desc, key="tab6_desc_input")

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

    col_hdr1, col_hdr2 = st.columns([3, 1])
    with col_hdr2:
        if st.button("➕ New Demo Draft (PENDING)", key="btn_create_fresh_draft"):
            import random
            rnd_id = f"DFT-00{random.randint(1, 999)}"
            approval_svc.create_draft(
                item_type="STORY",
                title="Configure Service Catalog Form Fields",
                payload={"id": rnd_id, "title": "Configure Service Catalog Form Fields", "description": "Define custom text and dropdown fields for catalog templates", "citations": ["PB-03"]}
            )
            st.rerun()

    drafts = approval_svc.get_all_drafts()
    pending_or_approved = [d for d in drafts if d.status in [DraftStatus.PENDING, DraftStatus.APPROVED]]

    if not pending_or_approved:
        # Automatically generate a clean PENDING demo draft DFT-001
        approval_svc.create_draft(
            item_type="STORY",
            title="Configure Service Catalog Form Fields",
            payload={"id": "DFT-001", "title": "Configure Service Catalog Form Fields", "description": "Define custom text and dropdown fields for catalog templates", "citations": ["PB-03"]}
        )
        drafts = approval_svc.get_all_drafts()

    # Sort drafts so PENDING & APPROVED appear at the top
    sorted_drafts = sorted(drafts, key=lambda d: 0 if d.status == DraftStatus.PENDING else (1 if d.status == DraftStatus.APPROVED else 2))

    st.subheader("Draft Queue Items")
    for d in sorted_drafts:
        expanded_default = (d.status in [DraftStatus.PENDING, DraftStatus.APPROVED])
        status_color = "🟡" if d.status == DraftStatus.PENDING else ("🟢" if d.status == DraftStatus.APPROVED else "⚪")
        with st.expander(f"{status_color} Draft: {d.title} (ID: `{d.id}`) — Status: **{d.status.value}**", expanded=expanded_default):
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
                        st.rerun()
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
