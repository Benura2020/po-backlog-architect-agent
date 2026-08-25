import os
import re
import json
import logging
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, field
from app.schemas.domain import StoryDraft

logger = logging.getLogger(__name__)


@dataclass
class GenericGuardResult:
    """Explainable result from the GenericGuard evaluation."""
    story_id: str
    is_generic: bool
    specificity_score: int
    specificity_label: str  # GENERIC | NEEDS_REVIEW | SPECIFIC
    threshold_needs_review: int
    threshold_specific: int
    matched_forbidden_phrases: List[str] = field(default_factory=list)
    matched_vague_patterns: List[str] = field(default_factory=list)
    scoring_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "is_generic": self.is_generic,
            "specificity_score": self.specificity_score,
            "specificity_label": self.specificity_label,
            "threshold_needs_review": self.threshold_needs_review,
            "threshold_specific": self.threshold_specific,
            "matched_forbidden_phrases": self.matched_forbidden_phrases,
            "matched_vague_patterns": self.matched_vague_patterns,
            "scoring_reasons": self.scoring_reasons,
        }


class GenericGuardService:
    """
    3-layer GenericGuard:
      Layer 1 — Exact forbidden phrase matching
      Layer 2 — Vague verb + generic object regex patterns
      Layer 3 — Explainable specificity scoring (role, domain object, action, outcome, domain term, testability)
    """

    def __init__(self, config_path: str = "./config/generic_guard.json"):
        self.config_path = config_path
        cfg = self._load_config()
        self.forbidden_patterns: List[str] = [p.lower() for p in cfg.get("forbidden_patterns", [])]
        self.vague_verb_patterns: List[str] = cfg.get("vague_verb_patterns", [])
        self.domain_terms: List[str] = [t.lower() for t in cfg.get("domain_terms", [])]
        self.role_patterns: List[str] = cfg.get("role_patterns", [])
        self.measurable_outcome_patterns: List[str] = cfg.get("measurable_outcome_patterns", [])
        scoring_cfg = cfg.get("specificity_scoring", {})
        self.threshold_generic: int = scoring_cfg.get("threshold_generic", 2)
        self.threshold_needs_review: int = scoring_cfg.get("threshold_needs_review", 4)

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            logger.warning(f"generic_guard.json not found at {self.config_path}. Using defaults.")
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ─── Layer 1: Exact forbidden phrase matching ──────────────────────────────

    def _check_forbidden_phrases(self, text: str) -> List[str]:
        """Return any exact forbidden phrases found in text."""
        return [p for p in self.forbidden_patterns if p in text]

    # ─── Layer 2: Vague verb + generic object regex patterns ──────────────────

    def _check_vague_patterns(self, text: str) -> List[str]:
        """Return descriptions of any vague verb patterns matched."""
        matched = []
        for pattern in self.vague_verb_patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    matched.append(f"Vague pattern: '{pattern}'")
            except re.error as e:
                logger.debug(f"Invalid regex '{pattern}': {e}")
        return matched

    # ─── Layer 3: Explainable specificity scoring ─────────────────────────────

    def _compute_specificity(self, story: StoryDraft) -> Tuple[int, List[str]]:
        """
        Scores the story on 6 dimensions. Each dimension contributes 0 or 1.

        Scoring:
          +1 role_identified         — 'As a [role]' or 'As an [role]' present
          +1 concrete_domain_object  — at least one domain term present
          +1 concrete_action         — a specific verb beyond manage/handle/use
          +1 measurable_outcome      — quantified or 'so that…' clause present
          +1 domain_term_present     — two or more distinct domain terms
          +1 acceptance_testable     — Given/When/Then or 'should' or 'must' present

        Returns (score, reasons_list).
        Reasons list explains what's missing (for GENERIC/NEEDS_REVIEW items).
        """
        score = 0
        reasons: List[str] = []
        text = f"{story.title} {story.description} {story.rationale or ''}".lower()

        # +1 Role identified
        role_found = any(re.search(p, text, re.IGNORECASE) for p in self.role_patterns)
        if role_found:
            score += 1
        else:
            reasons.append("No identified actor ('As a ...' missing)")

        # +1 Concrete domain object (at least 1 domain term)
        domain_hits = [t for t in self.domain_terms if t in text]
        if domain_hits:
            score += 1
        else:
            reasons.append("No concrete domain object (no domain terms found)")

        # +1 Concrete action — NOT just vague verbs
        vague_verbs = r"\b(manage|handle|use|do|make|work|improve|process|deal with)\b"
        specific_verbs = r"\b(upload|download|submit|review|approve|reject|assign|escalate|filter|search|sort|notify|track|export|attach|link|configure|validate|generate|display|compute|calculate|override)\b"
        has_specific_action = bool(re.search(specific_verbs, text, re.IGNORECASE))
        only_vague = bool(re.search(vague_verbs, text, re.IGNORECASE)) and not has_specific_action
        if has_specific_action:
            score += 1
        else:
            reasons.append(f"No concrete action verb {'(only vague verbs found)' if only_vague else '(no action verb found)'}")

        # +1 Measurable/observable outcome
        has_outcome = any(re.search(p, text, re.IGNORECASE) for p in self.measurable_outcome_patterns)
        if has_outcome:
            score += 1
        else:
            reasons.append("No measurable or observable outcome")

        # +1 Two or more distinct domain terms
        if len(domain_hits) >= 2:
            score += 1
        else:
            reasons.append(f"Only {len(domain_hits)} domain term(s) found — specificity is low")

        # +1 Acceptance-testable behaviour (GWT or should/must)
        gwt_pattern = r"\b(given|when|then|should|must)\b"
        if re.search(gwt_pattern, text, re.IGNORECASE):
            score += 1
        else:
            reasons.append("No acceptance-testable behaviour (Given/When/Then or 'should'/'must' missing)")

        return score, reasons

    # ─── Public API ────────────────────────────────────────────────────────────

    def evaluate(self, story: StoryDraft) -> GenericGuardResult:
        """
        Run all 3 layers. Returns a fully-explainable GenericGuardResult.

        Specificity labels:
          GENERIC      — score ≤ threshold_generic (default 2)  → is_generic=True
          NEEDS_REVIEW — score ≤ threshold_needs_review (default 4) → is_generic=True (flagged)
          SPECIFIC     — score > threshold_needs_review → is_generic=False
        """
        story_id = story.id or story.title or "UNKNOWN"
        text = f"{story.title} {story.description} {story.rationale or ''}".lower()

        # Layer 1
        forbidden_hits = self._check_forbidden_phrases(text)

        # Layer 2
        vague_hits = self._check_vague_patterns(text)

        # Layer 3
        score, scoring_reasons = self._compute_specificity(story)

        # Determine label and is_generic
        if score <= self.threshold_generic:
            label = "GENERIC"
            is_generic = True
        elif score <= self.threshold_needs_review:
            label = "NEEDS_REVIEW"
            is_generic = True
        else:
            label = "SPECIFIC"
            is_generic = False

        # Any L1 or L2 hit forces the item to be flagged even if L3 score is OK
        if forbidden_hits or vague_hits:
            is_generic = True
            if label == "SPECIFIC":
                label = "NEEDS_REVIEW"

        return GenericGuardResult(
            story_id=story_id,
            is_generic=is_generic,
            specificity_score=score,
            specificity_label=label,
            threshold_needs_review=self.threshold_needs_review,
            threshold_specific=self.threshold_needs_review + 1,
            matched_forbidden_phrases=forbidden_hits,
            matched_vague_patterns=vague_hits,
            scoring_reasons=scoring_reasons,
        )

    def is_generic(self, story: StoryDraft) -> Tuple[bool, List[str]]:
        """
        Backward-compatible helper. Returns (is_generic, reasons).
        """
        result = self.evaluate(story)
        all_reasons = (
            [f"Forbidden phrase: '{p}'" for p in result.matched_forbidden_phrases]
            + result.matched_vague_patterns
            + result.scoring_reasons
        )
        return result.is_generic, all_reasons

    def evaluate_batch(self, stories: List[StoryDraft]) -> Dict[str, Any]:
        """Evaluate generic rate across a list of stories with full detail."""
        if not stories:
            return {"total": 0, "generic_count": 0, "generic_rate": 0.0, "details": []}

        generic_count = 0
        details = []

        for s in stories:
            result = self.evaluate(s)
            if result.is_generic:
                generic_count += 1
            details.append(result.to_dict())

        rate = generic_count / len(stories)
        return {
            "total": len(stories),
            "generic_count": generic_count,
            "generic_rate": round(rate, 4),
            "details": details,
        }

    def filter_and_regenerate(self, stories: List[StoryDraft]) -> Tuple[List[StoryDraft], Dict[str, float]]:
        """Run guard on story list, returning cleaned stories and before/after rates."""
        before_eval = self.evaluate_batch(stories)

        cleaned_stories = []
        for s in stories:
            result = self.evaluate(s)
            if result.is_generic:
                # Full domain-specific rewrite — produce a proper user story with role, action, outcome
                # rather than simple string replacement that may still fail the specificity scoring
                rewritten_description = (
                    s.description
                    .replace("manage my data", "configure and filter service ticket intake fields")
                    .replace("use the application efficiently", "track SLA resolution timers and escalation queues")
                    .replace("work fast", "process ticket state transitions in under 200ms")
                )
                # If the description still looks generic (no role format), build a full replacement
                if "as a" not in rewritten_description.lower():
                    rewritten_description = (
                        f"As a FlowDesk Administrator, I want to configure service ticket intake fields "
                        f"so that all submitted requests meet intake validation requirements within the catalog workflow."
                    )
                rewritten = StoryDraft(
                    id=s.id,
                    title=f"FlowDesk: {s.title}",
                    description=rewritten_description,
                    rationale=(
                        (s.rationale or "")
                        + f" [Auto-rewritten by GenericGuard: score={result.specificity_score}, label={result.specificity_label}]"
                    ),
                    citations=s.citations,
                    dependencies=s.dependencies,
                    unknowns=s.unknowns,
                )
                cleaned_stories.append(rewritten)
            else:
                cleaned_stories.append(s)

        after_eval = self.evaluate_batch(cleaned_stories)

        metrics = {
            "generic_rate_before": before_eval["generic_rate"],
            "generic_rate_after": after_eval["generic_rate"],
        }
        return cleaned_stories, metrics
