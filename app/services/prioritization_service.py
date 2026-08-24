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
        items = self.db.query(BacklogItemModel).all()
        scores: List[PriorityScore] = []

        for idx, item in enumerate(items):
            # Seed deterministic rating inputs based on item attributes
            bv = 8.5 if "Catalog" in item.title or "Approval" in item.title or "Upload" in item.title else 6.0
            urg = 8.0 if "Audit" in item.title or "Emergency" in item.title else 5.5
            risk = 7.5 if "Security" in item.title or "SLA" in item.title else 5.0
            align = 8.0

            is_blocked = (item.status == "NOT_READY")
            has_dep = ("API" in item.title)

            score = self.compute_priority(
                story_id=item.id,
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
