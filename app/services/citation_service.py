from typing import List, Tuple
from sqlalchemy.orm import Session
from app.schemas.domain import Citation, UnsupportedClaim
from app.models.models import ContextSection


class CitationService:
    def __init__(self, db: Session):
        self.db = db

    def validate_citation_existence(self, citation: Citation) -> Tuple[bool, str]:
        """Assert citation resolves to a specific valid section in the context database."""
        if not citation.ref or citation.ref.strip() in ["product_brief.md", "DOCUMENT", "FULL"]:
            return False, "Citation ref points to whole document instead of a specific section ref (e.g. PB-04.1)"

        section = self.db.query(ContextSection).filter(ContextSection.ref == citation.ref.strip()).first()
        if not section:
            return False, f"Section ref '{citation.ref}' does not exist in indexed context DB"

        return True, "Valid section reference"

    def validate_citation_support(self, claim: str, citation: Citation) -> Tuple[bool, str]:
        """Validate if the referenced section text contains support for the claimed fact."""
        exists, msg = self.validate_citation_existence(citation)
        if not exists:
            return False, msg

        section = self.db.query(ContextSection).filter(ContextSection.ref == citation.ref.strip()).first()

        # Simple semantic keyword overlap verification
        claim_words = set([w.lower() for w in claim.split() if len(w) > 3])
        section_text = (section.title + " " + section.content).lower()

        matches = [w for w in claim_words if w in section_text]
        match_ratio = len(matches) / len(claim_words) if claim_words else 1.0

        if match_ratio < 0.3 and len(claim_words) > 2:
            return False, f"Section '{citation.ref}' text does not support claim '{claim}'"

        return True, "Supported claim"

    def check_citations(self, claims_and_citations: List[Tuple[str, Citation]]) -> Tuple[List[Citation], List[UnsupportedClaim]]:
        valid_citations: List[Citation] = []
        unsupported: List[UnsupportedClaim] = []

        for claim, citation in claims_and_citations:
            is_valid, reason = self.validate_citation_support(claim, citation)
            if is_valid:
                valid_citations.append(citation)
            else:
                unsupported.append(UnsupportedClaim(
                    claim=claim,
                    citation_ref=citation.ref,
                    reason=reason
                ))

        return valid_citations, unsupported
