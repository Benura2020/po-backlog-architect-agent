import os
import yaml
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.schemas.domain import DoRVerdict, DoRCheck
from app.models.models import BacklogItemModel, ApprovalLogModel
from app.services.generic_guard_service import GenericGuardService

logger = logging.getLogger(__name__)


class ReadinessService:
    def __init__(self, db: Session, config_path: str = "./config/readiness.yaml"):
        self.db = db
        self.config_path = config_path
        self.rules = self._load_rules()
        self.generic_guard = GenericGuardService()

    def _load_rules(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.config_path):
            return [
                {"id": "clear_user_value", "name": "Clear User Value"},
                {"id": "testable_criteria", "name": "Has Acceptance Criteria"},
                {"id": "grounded_citations", "name": "Grounded Citations"},
                {"id": "no_blocking_questions", "name": "No Blocking Questions"}
            ]
        with open(self.config_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content.get("rules", [])

    def evaluate_story(
        self,
        story_id: str,
        title: str,
        description: str,
        acceptance_criteria: str,
        citations: List[str],
        open_questions: List[str] = None,
        dependencies: List[str] = None
    ) -> DoRVerdict:
        checks: List[DoRCheck] = []
        blocking_reasons: List[str] = []
        suggested_actions: List[str] = []

        open_questions = open_questions or []
        dependencies = dependencies or []

        # 1. Clear user value format check
        has_role_format = "as a" in description.lower() and "i want" in description.lower()
        checks.append(DoRCheck(
            rule_id="clear_user_value",
            rule_name="Clear User Story Format",
            passed=has_role_format,
            details="Description contains 'As a [role], I want [action]'" if has_role_format else "Missing standard user story role format"
        ))
        if not has_role_format:
            blocking_reasons.append("Missing user story format 'As a [role], I want [action]'")
            suggested_actions.append("Reframe description into user story format")

        # 2. Testable criteria check
        has_criteria = bool(acceptance_criteria and len(acceptance_criteria.strip()) > 10)
        checks.append(DoRCheck(
            rule_id="testable_criteria",
            rule_name="Has Acceptance Criteria",
            passed=has_criteria,
            details="Acceptance criteria supplied" if has_criteria else "Acceptance criteria is empty or missing"
        ))
        if not has_criteria:
            blocking_reasons.append("No acceptance criteria supplied")
            suggested_actions.append("Generate Given/When/Then acceptance criteria")

        # 3. Grounded citations check
        has_citations = len(citations) > 0 and not any(c in ["DOCUMENT", ""] for c in citations)
        checks.append(DoRCheck(
            rule_id="grounded_citations",
            rule_name="Grounded Citations",
            passed=has_citations,
            details=f"Story references section citations {citations}" if has_citations else "Missing addressable section ref citations"
        ))
        if not has_citations:
            blocking_reasons.append("Story lacks grounded section ref citations")
            suggested_actions.append("Link story to specific section refs in product brief")

        # 4. No blocking questions check
        no_questions = len(open_questions) == 0
        checks.append(DoRCheck(
            rule_id="no_blocking_questions",
            rule_name="No Blocking Questions",
            passed=no_questions,
            details="0 unresolved open questions" if no_questions else f"Unresolved open questions: {open_questions}"
        ))
        if not no_questions:
            blocking_reasons.append(f"Unresolved questions blocking story: {open_questions}")
            suggested_actions.append("Resolve open questions with PO / stakeholders")

        # 5. Domain specific check (Anti-generic)
        from app.schemas.domain import StoryDraft
        dummy_story = StoryDraft(id=story_id, title=title, description=description, rationale="")
        is_gen, matches = self.generic_guard.is_generic(dummy_story)
        checks.append(DoRCheck(
            rule_id="domain_specific",
            rule_name="Domain Specific (Anti-Generic)",
            passed=not is_gen,
            details="Story is domain specific" if not is_gen else f"Contains generic phrases: {matches}"
        ))
        if is_gen:
            blocking_reasons.append(f"Story contains generic patterns: {matches}")
            suggested_actions.append("Rewrite story using domain specific concepts")

        status = "READY" if len(blocking_reasons) == 0 else "BLOCKED"

        return DoRVerdict(
            story_id=story_id,
            status=status,
            checks=checks,
            blocking_reasons=blocking_reasons,
            suggested_actions=suggested_actions
        )

    def record_human_override(self, story_id: str, actor: str, override_reason: str) -> DoRVerdict:
        """Record human override log entry to force status READY on a blocked story."""
        log_entry = ApprovalLogModel(
            id=f"OVR-{story_id}",
            draft_id=story_id,
            actor=actor,
            action="OVERRIDE",
            reason=override_reason
        )
        self.db.add(log_entry)
        self.db.commit()

        # Fetch story and evaluate base verdict
        item = self.db.query(BacklogItemModel).filter(BacklogItemModel.id == story_id).first()
        title = item.title if item else story_id
        desc = item.description if item else ""
        criteria = item.acceptance_criteria if item else ""

        verdict = self.evaluate_story(
            story_id=story_id,
            title=title,
            description=desc,
            acceptance_criteria=criteria,
            citations=["PB-01"]
        )
        verdict.status = "READY"
        verdict.human_overridden = True
        verdict.override_reason = override_reason
        return verdict
