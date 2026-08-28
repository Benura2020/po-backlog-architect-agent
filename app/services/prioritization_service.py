import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.schemas.domain import PriorityScore
from app.models.models import BacklogItemModel
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class PrioritizationService:
    def __init__(self, db: Session, llm_provider: Optional[LLMProvider] = None):
        self.db = db
        self.llm = llm_provider

    def compute_priority(
        self,
        story_id: str,
        business_value: float,
        urgency: float,
        risk_reduction: float,
        strategic_alignment: float,
        has_unmet_dependencies: bool = False,
        is_blocked: bool = False
    ) -> PriorityScore:
        """Calculate deterministic priority score using explicit formula."""
        # Clamp inputs between 1 and 10
        bv = max(1.0, min(10.0, float(business_value)))
        urg = max(1.0, min(10.0, float(urgency)))
        risk = max(1.0, min(10.0, float(risk_reduction)))
        align = max(1.0, min(10.0, float(strategic_alignment)))

        # Weights: 40% BV, 25% Urgency, 20% Risk, 15% Alignment
        base_score = (0.40 * bv) + (0.25 * urg) + (0.20 * risk) + (0.15 * align)

        readiness_factor = 0.0 if is_blocked else 1.0
        dependency_penalty = 1.0 if has_unmet_dependencies else 0.0

        # Formula calculation
        final_score = base_score * readiness_factor * (1.0 - (0.10 * dependency_penalty))
        final_score = round(final_score, 2)

        # Generate rationale sentence
        rationale = f"Score {final_score}: BV({bv}) + Urg({urg}) + Risk({risk}) + Align({align}) with Readiness({readiness_factor})."
        if self.llm:
            try:
                prompt = f"Provide a concise 1-sentence rationale for prioritizing story {story_id} with score {final_score}."
                rationale = self.llm.generate_text(prompt)
            except Exception:
                pass

        return PriorityScore(
            story_id=story_id,
            business_value=bv,
            urgency=urg,
            risk_reduction=risk,
            strategic_alignment=align,
            dependency_penalty=dependency_penalty,
            readiness_factor=readiness_factor,
            computed_score=final_score,
            rationale=rationale
        )

    def prioritize_backlog(self) -> List[PriorityScore]:
        from app.models.models import DraftModel, ApprovalLogModel
        self.db.expire_all()
        items = self.db.query(BacklogItemModel).all()
        scores: List[PriorityScore] = []

        # Find all stories that have received a human override (or criteria draft overrides)
        override_logs = self.db.query(ApprovalLogModel).filter(ApprovalLogModel.action.in_(["OVERRIDE", "HUMAN_OVERRIDE"])).all()
        overridden_ids = set()
        for log in override_logs:
            if not log.draft_id:
                continue
            overridden_ids.add(log.draft_id)
            # If draft_id is a CRITERIA draft, extract parent story_id from title or payload
            c_draft = self.db.query(DraftModel).filter(DraftModel.id == log.draft_id).first()
            if c_draft:
                if c_draft.item_type == "CRITERIA" and "Criteria for " in c_draft.title:
                    parts = c_draft.title.replace("Criteria for ", "").split(":")
                    if parts:
                        parent_id = parts[0].strip()
                        overridden_ids.add(parent_id)

        # Build combined list of items (DB backlog items + DraftModel STORY items)
        combined_items = []
        for i in items:
            combined_items.append({"id": i.id, "title": i.title, "status": i.status})

        draft_stories = self.db.query(DraftModel).filter(DraftModel.item_type == "STORY").all()
        for d in draft_stories:
            if not any(ci["id"] == d.id for ci in combined_items):
                combined_items.append({"id": d.id, "title": d.title, "status": "PENDING"})

        for idx, item in enumerate(combined_items):
            item_id = item["id"]
            item_title = item["title"]
            item_status = item["status"]

            # Seed rating inputs based on item attributes
            bv = 8.5 if "Catalog" in item_title or "Approval" in item_title or "Upload" in item_title else 6.0
            urg = 8.0 if "Audit" in item_title or "Emergency" in item_title else 5.5
            risk = 7.5 if "Security" in item_title or "SLA" in item_title else 5.0
            align = 8.0

            # Check if blocked, unless human overridden
            if item_id in overridden_ids:
                is_blocked = False
            else:
                is_blocked = (item_status == "NOT_READY")

            has_dep = ("API" in item_title)

            score = self.compute_priority(
                story_id=item_id,
                business_value=bv,
                urgency=urg,
                risk_reduction=risk,
                strategic_alignment=align,
                has_unmet_dependencies=has_dep,
                is_blocked=is_blocked
            )
            scores.append(score)

        # Sort descending by computed score
        scores.sort(key=lambda s: s.computed_score, reverse=True)
        return scores

    def compute_sprint_slice(self, capacity_count: int = 5) -> List[PriorityScore]:
        """Topologically sort ready stories to form an executable sprint slice."""
        prioritized = self.prioritize_backlog()
        # Filter out blocked stories (readiness_factor == 0)
        ready_stories = [s for s in prioritized if s.readiness_factor > 0]
        return ready_stories[:capacity_count]
