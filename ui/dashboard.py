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
if st.sidebar.button("🧹 Reset Demo / Clear All Drafts"):
    _db = get_db_session()
    _db.query(DraftModel).delete()
    _db.query(ApprovalLogModel).delete()
    _db.query(WriteLogModel).delete()
    _db.commit()
    _db.close()
    for k in ["last_decomposed_ids", "last_decomposed_epic", "tab3_title_input", "tab3_desc_input", "guard_title_input", "guard_desc_input"]:
        if k in st.session_state:
            del st.session_state[k]
    st.sidebar.success("Cleared all demo drafts and reset session state!")
    st.rerun()

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

            # Save generated stories as PENDING drafts for Tab 7
            approval_svc = ApprovalService(db)
            last_decomposed_ids = []
            for story in res.stories:
                draft = approval_svc.create_draft("STORY", story.title, story.model_dump())
                last_decomposed_ids.append(draft.id)
            # Store IDs in session so Tab 3 dropdown only shows THIS decomposition's stories
            st.session_state["last_decomposed_ids"] = last_decomposed_ids
            st.session_state["last_decomposed_epic"] = selected_epic["id"]

            if res.thin_epic_flag:
                st.warning("⚠️ THIN EPIC DETECTED: Agent produced open questions rather than inventing missing specifications.")

            st.success("Epic decomposed and drafts added to Tab 7 Approval Queue!")

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

    # Show contextual banner if stories from Tab 2 are available
    last_ep = st.session_state.get("last_decomposed_epic", "")
    last_ids = st.session_state.get("last_decomposed_ids", [])
    if last_ids:
        st.info(f"✨ **{len(last_ids)} decomposed stories from {last_ep} are pre-loaded** — select one below to generate criteria, or choose any backlog item.")
    else:
        st.info("💡 **Tip**: Decompose an epic in Tab 2 first — those stories will appear at the top of the dropdown here.")


    items = db.query(BacklogItemModel).all()
    if not items:
        from app.seed import seed_database
        seed_database()
        items = db.query(BacklogItemModel).all()

    # Fetch ONLY stories from the last decomposition run (stored in session_state)
    last_decomposed_ids = st.session_state.get("last_decomposed_ids", [])
    last_decomposed_epic = st.session_state.get("last_decomposed_epic", "")
    decomposed_options = []
    draft_lookup = {}
    if last_decomposed_ids:
        decomposed_drafts = db.query(DraftModel).filter(
            DraftModel.id.in_(last_decomposed_ids),
            DraftModel.item_type == "STORY"
        ).all()
        for d in decomposed_drafts:
            opt_str = f"✨ {d.id}: {d.title}"
            decomposed_options.append(opt_str)
            try:
                payload = json.loads(d.payload_json)
                draft_lookup[opt_str] = (d.id, d.title, payload.get("description", d.title))
            except Exception:
                draft_lookup[opt_str] = (d.id, d.title, d.title)

    backlog_options = [f"{i.id}: {i.title}" for i in items]
    # Show decomposed stories first (from the latest epic decomposition), then backlog items
    if decomposed_options:
        section_header = f"── Decomposed from {last_decomposed_epic} ──"
        item_options_tab3 = ["Custom Story / Free Text Input"] + decomposed_options + backlog_options
    else:
        section_header = ""
        item_options_tab3 = ["Custom Story / Free Text Input"] + backlog_options
    default_idx_tab3 = 0
    if decomposed_options:
        # Auto-select first decomposed story from the latest run
        default_idx_tab3 = 1  # index 0 is "Custom Story / Free Text Input"
    else:
        for idx, opt in enumerate(item_options_tab3):
            if "BL-006" in opt:
                default_idx_tab3 = idx
                break

    def on_tab3_select_change():
        sel = st.session_state.get("tab3_story_select")
        if sel and sel != "Custom Story / Free Text Input":
            if sel in draft_lookup:
                d_id, d_title, d_desc = draft_lookup[sel]
                st.session_state["tab3_title_input"] = d_title
                st.session_state["tab3_desc_input"] = d_desc
            else:
                sel_id = sel.split(":")[0]
                db_item = db.query(BacklogItemModel).filter(BacklogItemModel.id == sel_id).first()
                if db_item:
                    st.session_state["tab3_title_input"] = db_item.title
                    st.session_state["tab3_desc_input"] = db_item.description

    sel_story_tab3 = st.selectbox(
        "Select Backlog Story to Populate (or edit custom text below)",
        item_options_tab3,
        index=default_idx_tab3,
        key="tab3_story_select",
        on_change=on_tab3_select_change
    )

    default_title = "Upload Supporting Documents to Request"
    default_desc = "As a Requester, I want to attach PDF and image files to my service ticket so fulfillment agents have necessary context."
    selected_story_id = "BL-006"

    if sel_story_tab3 != "Custom Story / Free Text Input":
        # Handle decomposed drafts (✨ prefix) vs backlog items (BL-xxx: Title)
        if sel_story_tab3 in draft_lookup:
            d_id, d_title, d_desc = draft_lookup[sel_story_tab3]
            selected_story_id = d_id
            default_title = d_title
            default_desc = d_desc
        else:
            sel_id = sel_story_tab3.split(":")[0].strip()
            selected_story_id = sel_id
            db_item = db.query(BacklogItemModel).filter(BacklogItemModel.id == sel_id).first()
            if db_item:
                default_title = db_item.title
                default_desc = db_item.description

    if "tab3_title_input" not in st.session_state:
        st.session_state["tab3_title_input"] = default_title
    if "tab3_desc_input" not in st.session_state:
        st.session_state["tab3_desc_input"] = default_desc

    story_title = st.text_input("Story Title", key="tab3_title_input")
    story_desc = st.text_area("Story Description", key="tab3_desc_input")

    if st.button("Generate Acceptance Criteria"):
        agent = CriteriaAgent(llm, db)
        draft = agent.generate_criteria(selected_story_id, story_title, story_desc)

        # Save criteria as PENDING draft for Tab 7
        approval_svc = ApprovalService(db)
        approval_svc.create_draft("CRITERIA", f"Criteria for {selected_story_id}: {story_title}", draft.model_dump())

        st.success("Criteria generated successfully and draft added to Tab 7 Approval Queue!")

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

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📥 Load Decomposed Story into Guard"):
            st.session_state["guard_title_input"] = story_title
            st.session_state["guard_desc_input"] = story_desc
    with col_btn2:
        if st.button("⚠️ Load Generic Fluff Story (To Test Auto-Rewrite)"):
            st.session_state["guard_title_input"] = "Manage my data efficiently"
            st.session_state["guard_desc_input"] = "As a user I want to manage my data efficiently so that I can work."

    if "guard_title_input" not in st.session_state:
        st.session_state["guard_title_input"] = "Manage my data efficiently"
    if "guard_desc_input" not in st.session_state:
        st.session_state["guard_desc_input"] = "As a user I want to manage my data efficiently so that I can work."

    guard_title = st.text_input("Test Story Title for Specificity Check", key="guard_title_input")
    guard_desc = st.text_area("Test Story Description", key="guard_desc_input")

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

    # Include decomposed stories from last run if present
    last_decomposed_ids = st.session_state.get("last_decomposed_ids", [])
    decomposed_options = []
    draft_lookup_tab4 = {}
    if last_decomposed_ids:
        decomposed_drafts = db.query(DraftModel).filter(
            DraftModel.id.in_(last_decomposed_ids),
            DraftModel.item_type == "STORY"
        ).all()
        for d in decomposed_drafts:
            opt_str = f"✨ {d.id}: {d.title}"
            decomposed_options.append(opt_str)
            try:
                payload = json.loads(d.payload_json)
                ac_text = payload.get("acceptance_criteria", "")
                oq_list = payload.get("open_questions", [])

                # Check if Tab 3 generated criteria for this story
                crit_draft = db.query(DraftModel).filter(
                    DraftModel.item_type == "CRITERIA",
                    DraftModel.title.contains(d.id)
                ).first()

                if crit_draft:
                    c_payload = json.loads(crit_draft.payload_json)
                    happy_path = c_payload.get("happy_path", [])
                    if happy_path:
                        ac_lines = [f"Given {hp.get('given','')} When {hp.get('when','')} Then {hp.get('then','')}" for hp in happy_path]
                        ac_text = "\n".join(ac_lines)
                    c_oq = c_payload.get("open_questions", [])
                    if c_oq:
                        oq_list = [q.get("question", str(q)) if isinstance(q, dict) else str(q) for q in c_oq]

                draft_lookup_tab4[opt_str] = {
                    "id": d.id,
                    "title": d.title,
                    "description": payload.get("description", d.title),
                    "acceptance_criteria": ac_text,
                    "citations": payload.get("citations", []),
                    "open_questions": oq_list,
                    "dependencies": payload.get("dependencies", [])
                }
            except Exception:
                draft_lookup_tab4[opt_str] = {
                    "id": d.id, "title": d.title, "description": d.title,
                    "acceptance_criteria": "", "citations": [], "open_questions": [], "dependencies": []
                }

    backlog_options = [f"{i.id}: {i.title}" for i in items]
    item_options_tab4 = decomposed_options + backlog_options
    sel_item = st.selectbox("Select Backlog Story", item_options_tab4, key="tab4_story_select")

    if sel_item:
        readiness_svc = ReadinessService(db)
        if sel_item in draft_lookup_tab4:
            d_data = draft_lookup_tab4[sel_item]
            verdict = readiness_svc.evaluate_story(
                story_id=d_data["id"],
                title=d_data["title"],
                description=d_data["description"],
                acceptance_criteria=d_data["acceptance_criteria"],
                citations=[c.get("ref", c) if isinstance(c, dict) else str(c) for c in d_data["citations"]],
                open_questions=[q.get("question", q) if isinstance(q, dict) else str(q) for q in d_data["open_questions"]],
                dependencies=d_data["dependencies"]
            )
            item_id = d_data["id"]
        else:
            item_id = sel_item.split(":")[0].strip()
            db_item = db.query(BacklogItemModel).filter(BacklogItemModel.id == item_id).first()
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
            st.info("💡 **How to Fix / Unblock**: The Product Owner can review the open question above and record a **Human Override** below to promote this story to **READY** for sprint planning!")

        st.subheader("DoR Checklist Verification")
        for check in verdict.checks:
            icon = "✅" if check.passed else "❌"
            st.write(f"{icon} **{check.rule_name}**: {check.details}")

        st.divider()
        st.subheader("Human Override Log")
        override_actor = st.text_input("Override Actor Name", value="Human Lead PO")
        override_reason = st.text_area("Override Reason", value="Approved for sprint spike despite missing criteria.")
        if st.button("Record Human Override"):
            res = readiness_svc.record_human_override(item_id, override_actor, override_reason)
            st.warning(f"Override Recorded for {item_id}! Story status set to READY (Human Overridden).")

# TAB 5: PRIORITIZATION (O5)
with tabs[4]:
    st.header("📊 Deterministic Prioritization Engine (O5)")
    st.write("100% code arithmetic scoring formula with visible weights and topological dependency sorting.")

    st.latex(r"\text{Base} = 0.40 \cdot \text{BV} + 0.25 \cdot \text{Urg} + 0.20 \cdot \text{Risk} + 0.15 \cdot \text{Align}")
    st.latex(r"\text{Final} = \text{Base} \cdot \text{ReadinessFactor} \cdot (1 - 0.10 \cdot \text{DependencyPenalty})")

    db.expire_all()
    prio_svc = PrioritizationService(db, llm)
    prioritized = prio_svc.prioritize_backlog()

    # Identify decomposed and human-overridden story IDs
    last_decomposed_ids = st.session_state.get("last_decomposed_ids", [])
    override_logs = db.query(ApprovalLogModel).filter(ApprovalLogModel.action.in_(["OVERRIDE", "HUMAN_OVERRIDE"])).all()
    overridden_ids = set()
    for log in override_logs:
        if not log.draft_id:
            continue
        overridden_ids.add(log.draft_id)
        c_draft = db.query(DraftModel).filter(DraftModel.id == log.draft_id).first()
        if c_draft and c_draft.item_type == "CRITERIA" and "Criteria for " in c_draft.title:
            parts = c_draft.title.replace("Criteria for ", "").split(":")
            if parts:
                overridden_ids.add(parts[0].strip())

    # Summary box for Decomposed & Overridden stories
    decomposed_ranks = [p for p in prioritized if p.story_id in last_decomposed_ids or p.story_id in overridden_ids or "ST-" in p.story_id]
    if decomposed_ranks:
        st.info("✨ **Decomposed & Overridden Stories Status in Backlog Ranking:**")
        for p in decomposed_ranks:
            rank_idx = prioritized.index(p) + 1
            ov_flag = "🛠️ Human Overridden" if p.story_id in overridden_ids else ""
            st.success(f"**Rank #{rank_idx}** — Story `{p.story_id}` | Score: `{p.computed_score}` | Readiness: `{p.readiness_factor}` (READY) {ov_flag}")

    view_mode = st.radio("Filter Backlog Ranking", ["All Items", "Decomposed & Overridden Only"], horizontal=True)
    
    display_items = prioritized
    if view_mode == "Decomposed & Overridden Only":
        display_items = [p for p in prioritized if p.story_id in last_decomposed_ids or p.story_id in overridden_ids or "ST-" in p.story_id or "DFT-" in p.story_id]

    st.subheader(f"Prioritized Backlog Ranking ({len(display_items)} items)")
    for idx, p in enumerate(display_items):
        actual_rank = prioritized.index(p) + 1
        is_decomp = p.story_id in last_decomposed_ids or "ST-" in p.story_id or "DFT-" in p.story_id
        is_ov = p.story_id in overridden_ids

        badges = []
        if is_decomp:
            badges.append("✨ DECOMPOSED STORY")
        if is_ov:
            badges.append("🛠️ HUMAN OVERRIDDEN")

        status_badge = "✅ READY" if p.readiness_factor > 0 else "🛑 BLOCKED (Score = 0)"
        badge_str = f" [{' | '.join(badges)}]" if badges else ""

        st.markdown(f"### #{actual_rank} Story `{p.story_id}` — Score: `{p.computed_score}` ({status_badge}){badge_str}")
        st.caption(f"BV: {p.business_value} | Urg: {p.urgency} | Risk: {p.risk_reduction} | Align: {p.strategic_alignment} | Readiness: {p.readiness_factor} | Dep Penalty: {p.dependency_penalty}")
        st.write(f"*Rationale*: {p.rationale}")

# TAB 6: OVERLAP DETECTOR (O7)
with tabs[5]:
    st.header("🔄 Backlog Overlap Detection (O7)")
    st.write("Detect relationship types (`DUPLICATE`, `SUBSET`, `SUPERSET`, `ADJACENT`) between new stories and existing backlog.")

    # Include decomposed stories in Tab 6 dropdown
    last_decomposed_ids = st.session_state.get("last_decomposed_ids", [])
    decomposed_options_tab6 = []
    draft_lookup_tab6 = {}
    if last_decomposed_ids:
        decomposed_drafts = db.query(DraftModel).filter(
            DraftModel.id.in_(last_decomposed_ids),
            DraftModel.item_type == "STORY"
        ).all()
        for d in decomposed_drafts:
            opt_str = f"✨ {d.id}: {d.title}"
            decomposed_options_tab6.append(opt_str)
            try:
                payload = json.loads(d.payload_json)
                draft_lookup_tab6[opt_str] = (d.id, d.title, payload.get("description", d.title))
            except Exception:
                draft_lookup_tab6[opt_str] = (d.id, d.title, d.title)

    backlog_options_tab6 = [f"{i.id}: {i.title}" for i in items]
    item_options_tab6 = ["Custom Story / Free Text Input"] + decomposed_options_tab6 + backlog_options_tab6
    default_idx_tab6 = 0
    if decomposed_options_tab6:
        default_idx_tab6 = 1
    else:
        for idx, opt in enumerate(item_options_tab6):
            if "BL-006" in opt:
                default_idx_tab6 = idx
                break

    def on_tab6_select_change():
        sel = st.session_state.get("tab6_story_select")
        if sel and sel != "Custom Story / Free Text Input":
            if sel in draft_lookup_tab6:
                d_id, d_title, d_desc = draft_lookup_tab6[sel]
                st.session_state["tab6_title_input"] = d_title
                st.session_state["tab6_desc_input"] = d_desc
            else:
                sel_id = sel.split(":")[0].strip()
                db_item = db.query(BacklogItemModel).filter(BacklogItemModel.id == sel_id).first()
                if db_item:
                    st.session_state["tab6_title_input"] = db_item.title
                    st.session_state["tab6_desc_input"] = db_item.description

    sel_story_tab6 = st.selectbox(
        "Select Candidate Story to Populate (or edit custom text below)",
        item_options_tab6,
        index=default_idx_tab6,
        key="tab6_story_select",
        on_change=on_tab6_select_change
    )

    default_ov_title = "Upload Supporting Documents to Request"
    default_ov_desc = "As a Requester, I want to attach PDF files to my ticket"

    if sel_story_tab6 != "Custom Story / Free Text Input":
        if sel_story_tab6 in draft_lookup_tab6:
            _, d_title, d_desc = draft_lookup_tab6[sel_story_tab6]
            default_ov_title = d_title
            default_ov_desc = d_desc
        else:
            sel_id = sel_story_tab6.split(":")[0].strip()
            db_item = db.query(BacklogItemModel).filter(BacklogItemModel.id == sel_id).first()
            if db_item:
                default_ov_title = db_item.title
                default_ov_desc = db_item.description

    if "tab6_title_input" not in st.session_state:
        st.session_state["tab6_title_input"] = default_ov_title
    if "tab6_desc_input" not in st.session_state:
        st.session_state["tab6_desc_input"] = default_ov_desc

    ov_title = st.text_input("New Story Title", key="tab6_title_input")
    ov_desc = st.text_area("New Story Description", key="tab6_desc_input")

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
        import uuid
        fresh_id = f"DFT-{uuid.uuid4().hex[:4].upper()}"
        existing_dft1 = db.query(DraftModel).filter(DraftModel.id == "DFT-001").first()
        if not existing_dft1:
            fresh_id = "DFT-001"

        approval_svc.create_draft(
            item_type="STORY",
            title="Configure Service Catalog Form Fields",
            payload={"id": fresh_id, "title": "Configure Service Catalog Form Fields", "description": "Define custom text and dropdown fields for catalog templates", "citations": ["PB-03"]}
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
                    msg = f"🟢 DRAFT APPROVED: {d.id} is now APPROVED and unlocked for tracker export."
                    print(f"\n[APPROVAL GATE] {msg}\n")
                    st.session_state[f"msg_{d.id}"] = ("success", msg)
                    st.rerun()

            with col_b:
                if st.button(f"Reject {d.id}", key=f"rej_{d.id}"):
                    approval_svc.reject_draft(d.id, "Human PO", "Rejected in Streamlit UI")
                    msg = f"🔴 DRAFT REJECTED: {d.id} is now REJECTED. Any future write attempts will return HTTP 403 Forbidden."
                    print(f"\n[APPROVAL GATE] {msg}\n")
                    st.session_state[f"msg_{d.id}"] = ("warning", msg)
                    st.rerun()

            with col_c:
                if st.button(f"Write to MockTracker ({d.id})", key=f"wr_{d.id}"):
                    try:
                        record = approval_svc.write_draft_to_tracker(d.id)
                        msg = f"✅ SUCCESS (HTTP 200): Wrote draft {d.id} to MockTracker as item {record['id']} | Tags: {record['tags']} | Enforced Status: {record['status']}"
                        print(f"\n[APPROVAL GATE] {msg}\n")
                        st.session_state[f"msg_{d.id}"] = ("success", msg)
                        st.rerun()
                    except (ApprovalRequiredError, AlreadyWrittenError) as e:
                        msg = f"❌ WRITE BLOCKED BY SERVICE LAYER (HTTP 403 / 409): {e}"
                        print(f"\n[APPROVAL GATE] {msg}\n")
                        st.session_state[f"msg_{d.id}"] = ("error", msg)
                        st.rerun()

            # Render persistent feedback message if present
            if f"msg_{d.id}" in st.session_state:
                m_type, m_text = st.session_state[f"msg_{d.id}"]
                if m_type == "success":
                    st.success(m_text)
                elif m_type == "warning":
                    st.warning(m_text)
                elif m_type == "error":
                    st.error(m_text)

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
