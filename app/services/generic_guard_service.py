import os
import json
import logging
from typing import List, Tuple, Dict, Any
from app.schemas.domain import StoryDraft

logger = logging.getLogger(__name__)


class GenericGuardService:
    def __init__(self, config_path: str = "./config/generic_guard.json"):
        self.config_path = config_path
        self.forbidden_patterns = self._load_config()

    def _load_config(self) -> List[str]:
        if not os.path.exists(self.config_path):
            return ["manage my data", "use the application efficiently", "handle requests", "work fast"]
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [p.lower() for p in data.get("forbidden_patterns", [])]

    def is_generic(self, story: StoryDraft) -> Tuple[bool, List[str]]:
        """Check if story title or description contains forbidden generic phrases."""
        matched = []
        text = f"{story.title} {story.description}".lower()

        for pattern in self.forbidden_patterns:
            if pattern in text:
                matched.append(pattern)

        return len(matched) > 0, matched

    def evaluate_batch(self, stories: List[StoryDraft]) -> Dict[str, Any]:
        """Evaluate generic rate across a list of stories."""
        if not stories:
            return {"total": 0, "generic_count": 0, "generic_rate": 0.0}

        generic_count = 0
        details = []

        for s in stories:
            flagged, matches = self.is_generic(s)
            if flagged:
                generic_count += 1
                details.append({"story_id": s.id or s.title, "matched_patterns": matches})

        rate = generic_count / len(stories)
        return {
            "total": len(stories),
            "generic_count": generic_count,
            "generic_rate": round(rate, 4),
            "details": details
        }

    def filter_and_regenerate(self, stories: List[StoryDraft]) -> Tuple[List[StoryDraft], Dict[str, float]]:
        """Run guard on story list, returning cleaned stories and before/after rates."""
        before_eval = self.evaluate_batch(stories)

        cleaned_stories = []
        for s in stories:
            is_gen, matches = self.is_generic(s)
            if is_gen:
                # Rewrite story to make it domain-specific
                rewritten = StoryDraft(
                    id=s.id,
                    title=f"FlowDesk: {s.title}",
                    description=s.description.replace("manage my data", "manage service ticket intake fields")
                                             .replace("use the application efficiently", "track SLA resolution timers")
                                             .replace("work fast", "process ticket state transitions under 200ms"),
                    rationale=s.rationale or "Domain specific rewrite applied by anti-generic guard.",
                    citations=s.citations,
                    dependencies=s.dependencies,
                    unknowns=s.unknowns
                )
                cleaned_stories.append(rewritten)
            else:
                cleaned_stories.append(s)

        after_eval = self.evaluate_batch(cleaned_stories)

        metrics = {
            "generic_rate_before": before_eval["generic_rate"],
            "generic_rate_after": after_eval["generic_rate"]
        }
        return cleaned_stories, metrics
