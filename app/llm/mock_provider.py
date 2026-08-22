from typing import Optional, Type, Dict, Any
from pydantic import BaseModel
from app.llm.base import LLMProvider
from app.schemas.domain import (
    AcceptanceCriteriaDraft,
    GWTCriterion,
    OpenQuestion,
    Citation,
    StoryDraft,
    EpicDecompositionResult,
    UnsupportedClaim
)


class MockProvider(LLMProvider):
    """Deterministic Mock Provider for zero-cost offline testing and repeatable evals."""

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if "priority" in prompt.lower():
            return "High business value and core operational impact justify sprint inclusion."
        return "Mock rationale statement based on FlowDesk domain criteria."

    def generate_json(self, prompt: str, schema: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
        # 1. Acceptance Criteria Draft
        if schema == AcceptanceCriteriaDraft or "AcceptanceCriteriaDraft" in schema.__name__:
            # Detect file upload planted gap
            if "upload" in prompt.lower() or "file" in prompt.lower() or "pb-04" in prompt.lower():
                return AcceptanceCriteriaDraft(
                    story_id="BL-006",
                    happy_path=[
                        GWTCriterion(
                            given="A user is on the request form",
                            when="They attach a valid PDF document",
                            then="The file is stored and displayed under ticket attachments"
                        )
                    ],
                    alternatives=[],
                    edge_cases=[],
                    non_functional=[],
                    open_questions=[
                        OpenQuestion(
                            question="What is the maximum permitted file size for document uploads?",
                            reason="Section PB-04.2 states large files are rejected but specifies no exact byte limit",
                            missing_concept="maximum permitted file size"
                        )
                    ],
                    unsupported_claims=[],
                    citations=[Citation(source="product_brief.md", ref="PB-04.1", quote="The file intake pipeline accepts document formats")]
                )
            else:
                return AcceptanceCriteriaDraft(
                    story_id="BL-005",
                    happy_path=[
                        GWTCriterion(
                            given="A department lead opens the reporting tab",
                            when="The dashboard loads",
                            then="Counts for SUBMITTED, IN_PROGRESS, and RESOLVED tickets are displayed"
                        )
                    ],
                    open_questions=[],
                    citations=[Citation(source="product_brief.md", ref="PB-11", quote="Department Leads have access to operational analytics dashboards")]
                )

        # 2. Epic Decomposition Result
        if schema == EpicDecompositionResult or "EpicDecompositionResult" in schema.__name__:
            if "thin" in prompt.lower() or "ep-002" in prompt.lower():
                # Golden Case 8: Thin epic produces open_questions > stories
                return EpicDecompositionResult(
                    epic_id="EP-002",
                    thin_epic_flag=True,
                    stories=[
                        StoryDraft(
                            id="ST-MOCK-001",
                            title="Execute Emergency Approval Override",
                            description="As a Department Lead, I want to manually override stalled approvals so critical tickets progress.",
                            rationale="Supported by PB-06.2 emergency override path.",
                            citations=[Citation(source="product_brief.md", ref="PB-06.2", quote="Approvers can override rejected requests")]
                        )
                    ],
                    open_questions=[
                        OpenQuestion(
                            question="Which role is authorized to perform approval overrides?",
                            reason="Section PB-06.2 refers to approvers but does not specify exact system role names",
                            missing_concept="authorized approver role"
                        ),
                        OpenQuestion(
                            question="What SLA breach threshold triggers an automated override task?",
                            reason="Section PB-06.2 mentions stalled approvals without detailing the exact time limit",
                            missing_concept="approval stall SLA threshold"
                        )
                    ]
                )
            else:
                # Detailed epic EP-001
                return EpicDecompositionResult(
                    epic_id="EP-001",
                    thin_epic_flag=False,
                    stories=[
                        StoryDraft(
                            id="ST-018",
                            title="Upload Supporting Documents to Ticket",
                            description="As a Requester, I want to attach supporting PDF and image files to my service request so fulfillment agents have necessary context.",
                            rationale="Enables ticket attachment intake defined in PB-04.1.",
                            citations=[Citation(source="product_brief.md", ref="PB-04.1", quote="The file intake pipeline accepts document formats including PDF, DOCX, XLSX")]
                        ),
                        StoryDraft(
                            id="ST-019",
                            title="Validate Uploaded File Formats at Edge Gateway",
                            description="As a System Administrator, I want security filters to block executable attachments before storage so malicious code is prevented.",
                            rationale="Required security control per PB-04.1.",
                            citations=[Citation(source="product_brief.md", ref="PB-04.1", quote="System security filters automatically scan uploaded artifacts for executable payloads")]
                        ),
                        StoryDraft(
                            id="ST-020",
                            title="Enforce File Upload Size Limits",
                            description="As a System Administrator, I want large files rejected at the edge gateway with HTTP 413 so bandwidth is preserved.",
                            rationale="Enforces gateway policy per PB-04.2.",
                            citations=[Citation(source="product_brief.md", ref="PB-04.2", quote="Large files are rejected at the edge gateway during form submission")]
                        )
                    ],
                    open_questions=[
                        OpenQuestion(
                            question="What is the maximum permitted file size?",
                            reason="PB-04.2 states large files are rejected without specifying size threshold",
                            missing_concept="max file size"
                        )
                    ]
                )

        # Fallback empty model initialization
        return schema()
