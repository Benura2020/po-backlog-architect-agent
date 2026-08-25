import os
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.llm.groq_provider import GroqProvider
from app.llm.mock_provider import MockProvider
from app.services.context_service import ContextService
from app.services.citation_service import CitationService
from app.agents.criteria_agent import CriteriaAgent
from app.agents.decomposition_agent import DecompositionAgent
from app.services.generic_guard_service import GenericGuardService
from app.services.readiness_service import ReadinessService
from app.services.approval_service import ApprovalService, ApprovalRequiredError, AlreadyWrittenError
from app.services.prioritization_service import PrioritizationService
from app.services.overlap_service import OverlapService
from app.schemas.domain import (
    AcceptanceCriteriaDraft,
    EpicDecompositionResult,
    DoRVerdict,
    PriorityScore,
    OverlapResult,
    DraftStatus
)

router = APIRouter()


def get_llm():
    provider = os.getenv("LLM_PROVIDER", "mock")
    if provider.lower() == "groq" and os.getenv("GROQ_API_KEY"):
        return GroqProvider()
    return MockProvider()


# 1. Context Endpoints (O1)
@router.post("/context/index")
def index_context(doc_name: str = "product_brief.md", db: Session = Depends(get_db)):
    service = ContextService(db)
    path = os.path.join(os.getenv("DATA_DIR", "./data"), doc_name)
    count = service.index_markdown(path, doc_name=doc_name)
    return {"status": "success", "sections_indexed": count}


@router.get("/context/search")
def search_context(q: str, limit: int = 5, db: Session = Depends(get_db)):
    service = ContextService(db)
    return service.search_context(q, limit=limit)


@router.get("/context/sections/{ref}")
def get_section(ref: str, db: Session = Depends(get_db)):
    service = ContextService(db)
    sec = service.get_section(ref)
    if not sec:
        raise HTTPException(status_code=404, detail="Section reference not found")
    return {"ref": sec.ref, "title": sec.title, "content": sec.content, "document_name": sec.document_name}


# 2. Criteria Generator Endpoint (O3, O6)
@router.post("/criteria/generate", response_model=AcceptanceCriteriaDraft)
def generate_criteria(story_id: str, title: str, description: str, db: Session = Depends(get_db)):
    agent = CriteriaAgent(get_llm(), db)
    draft = agent.generate_criteria(story_id, title, description)

    # Save as draft in PENDING state
    approval_svc = ApprovalService(db)
    approval_svc.create_draft("CRITERIA", f"Criteria for {story_id}", draft.model_dump())

    return draft


# 3. Epic Decomposition Endpoint (O2)
@router.post("/epics/decompose", response_model=EpicDecompositionResult)
def decompose_epic(epic_id: str, title: str, description: str, is_thin: bool = False, db: Session = Depends(get_db)):
    agent = DecompositionAgent(get_llm(), db)
    result = agent.decompose_epic(epic_id, title, description, is_thin=is_thin)

    approval_svc = ApprovalService(db)
    for story in result.stories:
        approval_svc.create_draft("STORY", story.title, story.model_dump())

    return result


# 4. Readiness Gate Endpoints (O4)
@router.post("/readiness/evaluate", response_model=DoRVerdict)
def evaluate_readiness(
    story_id: str,
    title: str,
    description: str,
    acceptance_criteria: str = "",
    citations: List[str] = [],
    db: Session = Depends(get_db)
):
    service = ReadinessService(db)
    return service.evaluate_story(story_id, title, description, acceptance_criteria, citations)


@router.post("/readiness/override")
def override_readiness(story_id: str, actor: str, reason: str, db: Session = Depends(get_db)):
    service = ReadinessService(db)
    return service.record_human_override(story_id, actor, reason)


# 5. Prioritization Endpoints (O5)
@router.post("/prioritization/calculate", response_model=PriorityScore)
def calculate_priority(
    story_id: str,
    business_value: float,
    urgency: float,
    risk_reduction: float,
    strategic_alignment: float,
    has_unmet_dependencies: bool = False,
    is_blocked: bool = False,
    db: Session = Depends(get_db)
):
    service = PrioritizationService(db, get_llm())
    return service.compute_priority(
        story_id, business_value, urgency, risk_reduction, strategic_alignment, has_unmet_dependencies, is_blocked
    )


@router.get("/prioritization/backlog", response_model=List[PriorityScore])
def get_prioritized_backlog(db: Session = Depends(get_db)):
    service = PrioritizationService(db, get_llm())
    return service.prioritize_backlog()


# 6. Overlap Detection Endpoint (O7)
@router.post("/overlap/check", response_model=List[OverlapResult])
def check_overlap(title: str, description: str, db: Session = Depends(get_db)):
    from app.schemas.domain import StoryDraft
    story = StoryDraft(title=title, description=description, rationale="")
    service = OverlapService(db)
    return service.check_overlap(story)


# 7. Approval & Write Gate Endpoints (O9 - Structurally Gated)
@router.get("/approval/drafts")
def list_drafts(db: Session = Depends(get_db)):
    service = ApprovalService(db)
    drafts = service.get_all_drafts()
    return [{"id": d.id, "title": d.title, "type": d.item_type, "status": d.status} for d in drafts]


@router.post("/approval/approve")
def approve_draft(draft_id: str, actor: str = "Human PO", reason: str = "Approved in UI", db: Session = Depends(get_db)):
    service = ApprovalService(db)
    draft = service.approve_draft(draft_id, actor, reason)
    return {"status": "success", "draft_id": draft.id, "new_status": draft.status}


@router.post("/approval/reject")
def reject_draft(draft_id: str, actor: str = "Human PO", reason: str = "Rejected in UI", db: Session = Depends(get_db)):
    service = ApprovalService(db)
    draft = service.reject_draft(draft_id, actor, reason)
    return {"status": "success", "draft_id": draft.id, "new_status": draft.status}


@router.post("/approval/write-tracker")
def write_tracker(draft_id: str, db: Session = Depends(get_db)):
    service = ApprovalService(db)
    try:
        record = service.write_draft_to_tracker(draft_id)
        return {"status": "success", "record": record}
    except ApprovalRequiredError as e:
        # 403 Forbidden — caller is not permitted to write in current draft state (PENDING or REJECTED)
        raise HTTPException(status_code=403, detail=str(e))
    except AlreadyWrittenError as e:
        # 409 Conflict — idempotency violation, draft has already been written to tracker
        raise HTTPException(status_code=409, detail=str(e))
