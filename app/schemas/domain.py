from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class DraftStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WRITTEN = "WRITTEN"


class OverlapType(str, Enum):
    DUPLICATE = "DUPLICATE"
    SUBSET = "SUBSET"
    SUPERSET = "SUPERSET"
    ADJACENT = "ADJACENT"
    NONE = "NONE"


class Citation(BaseModel):
    source: str = Field(description="Document source, e.g. 'product_brief' or 'glossary'")
    ref: str = Field(description="Addressable section ref, e.g. 'PB-04.2' or 'GL-05'")
    quote: Optional[str] = Field(default=None, description="Exact snippet quoted from the section")


class OpenQuestion(BaseModel):
    question: str = Field(description="Specific question identifying the missing requirement or ambiguity")
    reason: str = Field(description="Why this question is necessary and what risk it mitigates")
    missing_concept: str = Field(description="The concept missing from context, e.g., 'max file size'")


class UnsupportedClaim(BaseModel):
    claim: str = Field(description="Claim made that lacks grounding in source context")
    citation_ref: str = Field(description="Referenced ref that failed verification")
    reason: str = Field(description="Why the citation fails to support the claim")


class GWTCriterion(BaseModel):
    given: str = Field(description="Initial context / state")
    when: str = Field(description="Action or event")
    then: str = Field(description="Expected outcome or assertion")


class AcceptanceCriteriaDraft(BaseModel):
    story_id: str
    happy_path: List[GWTCriterion] = Field(default_factory=list)
    alternatives: List[GWTCriterion] = Field(default_factory=list)
    edge_cases: List[GWTCriterion] = Field(default_factory=list)
    non_functional: List[GWTCriterion] = Field(default_factory=list)
    open_questions: List[OpenQuestion] = Field(default_factory=list, description="REQUIRED field for gaps")
    unsupported_claims: List[UnsupportedClaim] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)


class StoryDraft(BaseModel):
    id: Optional[str] = None
    title: str
    description: str = Field(description="User story format: As a [role], I want [action] so that [benefit]")
    rationale: str = Field(description="Business and domain justification based on context")
    citations: List[Citation] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    unknowns: List[OpenQuestion] = Field(default_factory=list)


class EpicDecompositionResult(BaseModel):
    epic_id: str
    stories: List[StoryDraft] = Field(default_factory=list)
    open_questions: List[OpenQuestion] = Field(default_factory=list)
    thin_epic_flag: bool = False


class DoRCheck(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    details: str


class DoRVerdict(BaseModel):
    story_id: str
    status: str = Field(description="'READY' or 'BLOCKED'")
    checks: List[DoRCheck]
    blocking_reasons: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    human_overridden: bool = False
    override_reason: Optional[str] = None


class PriorityScore(BaseModel):
    story_id: str
    business_value: float = Field(ge=1, le=10, description="Business value rating 1-10")
    urgency: float = Field(ge=1, le=10, description="Urgency rating 1-10")
    risk_reduction: float = Field(ge=1, le=10, description="Risk reduction rating 1-10")
    strategic_alignment: float = Field(ge=1, le=10, description="Strategic alignment rating 1-10")
    dependency_penalty: float = Field(default=0.0, description="0.0 if dependencies met, 1.0 if unmet")
    readiness_factor: float = Field(default=1.0, description="1.0 if READY, 0.0 if BLOCKED")
    computed_score: float = Field(description="Deterministic score calculated via formula")
    rationale: str = Field(description="One sentence summary explanation")


class OverlapResult(BaseModel):
    target_story_id: str
    existing_item_id: str
    relationship_type: OverlapType
    recommendation: str
    confidence: float
