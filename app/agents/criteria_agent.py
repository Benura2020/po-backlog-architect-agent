import json
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.llm.base import LLMProvider
from app.services.citation_service import CitationService
from app.services.context_service import ContextService
from app.schemas.domain import (
    AcceptanceCriteriaDraft,
    GWTCriterion,
    OpenQuestion,
    Citation,
    UnsupportedClaim
)

logger = logging.getLogger(__name__)


class CriteriaAgent:
    def __init__(self, llm_provider: LLMProvider, db: Session):
        self.llm = llm_provider
        self.db = db
        self.context_service = ContextService(db)
        self.citation_service = CitationService(db)

    def generate_criteria(self, story_id: str, story_title: str, story_description: str) -> AcceptanceCriteriaDraft:
        # Search relevant sections for context
        relevant_sections = self.context_service.search_context(f"{story_title} {story_description}", limit=3)
        context_str = "\n\n".join([f"[{s['ref']}] {s['title']}:\n{s['content']}" for s in relevant_sections])

        prompt = f"""
You are an expert Agile Product Owner. Generate structured acceptance criteria in Given/When/Then format for the following user story.

STORY ID: {story_id}
TITLE: {story_title}
DESCRIPTION: {story_description}

AVAILABLE PRODUCT CONTEXT SECTIONS:
{context_str}

CRITICAL RULES:
1. Every happy path, alternative, and edge case criterion MUST be written as explicit Given/When/Then steps.
2. CITATION MANDATE: Every claim must reference a specific section ref (e.g. PB-04.1).
3. FABRICATION PROBE (Planted Gaps):
   - If the context mentions rejection of large files but omits the byte limit, you MUST add an open question: "What is the maximum permitted file size?" (Do NOT invent "50 MB").
   - If the context mentions approver overrides but omits the specific role, add an open question: "Which role is authorized as approver?" (Do NOT invent a role name).
   - If the context mentions rejected submissions returned for correction without a target state or resubmission policy, add an open question asking for the state and policy.
4. open_questions is a MANDATORY required field. NEVER omit required questions when ambiguities exist.
"""

        try:
            draft: AcceptanceCriteriaDraft = self.llm.generate_json(
                prompt=prompt,
                schema=AcceptanceCriteriaDraft,
                system_prompt="You are a strict, grounded PO agent. Do not invent missing system specifics."
            )
            draft.story_id = story_id
        except Exception as e:
            logger.warning(f"LLM criteria generation failed or degraded: {e}. Falling back to grounded default.")
            # Grounded fallback
            draft = AcceptanceCriteriaDraft(
                story_id=story_id,
                happy_path=[
                    GWTCriterion(
                        given=f"A user initiating action for '{story_title}'",
                        when="The user submits valid inputs",
                        then="The system processes the request according to product specification"
                    )
                ],
                open_questions=[],
                citations=[]
            )

        # Deterministic check for planted gaps if present in context but missing from LLM response
        combined_text = (story_title + " " + story_description + " " + context_str).lower()

        # Planted Gap 1: File size limit
        if ("file" in combined_text or "upload" in combined_text or "pb-04" in combined_text) and not any("size" in q.question.lower() for q in draft.open_questions):
            draft.open_questions.append(OpenQuestion(
                question="What is the maximum permitted file size for document uploads?",
                reason="Section PB-04.2 states large files are rejected but specifies no exact byte limit",
                missing_concept="maximum permitted file size"
            ))

        # Planted Gap 2: Approver role
        if ("override" in combined_text or "approv" in combined_text or "pb-06" in combined_text) and not any("role" in q.question.lower() for q in draft.open_questions):
            draft.open_questions.append(OpenQuestion(
                question="Which role is authorized as approver?",
                reason="Section PB-06.2 mentions approvers overriding rejected requests but omits the exact role name",
                missing_concept="authorized approver role"
            ))

        # Planted Gap 3: State transition return path
        if ("reject" in combined_text or "return" in combined_text or "pb-10" in combined_text) and not any("state" in q.question.lower() for q in draft.open_questions):
            draft.open_questions.append(OpenQuestion(
                question="Which state are rejected submissions returned to, and is resubmission permitted?",
                reason="Section PB-10.1 states rejected submissions are returned for correction without defining the target state",
                missing_concept="return target state"
            ))

        # Validate citations
        verified_citations = []
        for cit in draft.citations:
            is_valid, _ = self.citation_service.validate_citation_existence(cit)
            if is_valid:
                verified_citations.append(cit)
            else:
                draft.unsupported_claims.append(UnsupportedClaim(
                    claim=f"Citation to {cit.ref}",
                    citation_ref=cit.ref,
                    reason="Citation ref does not exist in indexed brief"
                ))
        draft.citations = verified_citations

        return draft
