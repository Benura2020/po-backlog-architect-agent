import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import DraftModel, ApprovalLogModel, WriteLogModel
from app.schemas.domain import DraftStatus
from app.adapters.tracker import Tracker, MockTracker

logger = logging.getLogger(__name__)


class ApprovalRequiredError(Exception):
    """Raised when an unapproved draft attempts an external tracker write."""
    pass


class AlreadyWrittenError(Exception):
    """Raised when an already-written draft attempts a duplicate tracker write."""
    pass


class ApprovalService:
    def __init__(self, db: Session, tracker: Optional[Tracker] = None):
        self.db = db
        self.tracker = tracker or MockTracker()

    def create_draft(self, item_type: str, title: str, payload: Dict[str, Any]) -> DraftModel:
        draft_id = payload.get("id") or f"DFT-{uuid.uuid4().hex[:6].upper()}"
        draft = DraftModel(
            id=draft_id,
            item_type=item_type,
            title=title,
            payload_json=json.dumps(payload),
            status=DraftStatus.PENDING
        )
        self.db.add(draft)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def approve_draft(self, draft_id: str, actor: str, reason: Optional[str] = None) -> DraftModel:
        draft = self.db.query(DraftModel).filter(DraftModel.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")

        draft.status = DraftStatus.APPROVED
        draft.updated_at = datetime.utcnow()

        log = ApprovalLogModel(
            id=f"LOG-{draft_id}-{datetime.utcnow().timestamp()}",
            draft_id=draft_id,
            actor=actor,
            action="APPROVED",
            reason=reason or "Human approved in approval queue"
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def reject_draft(self, draft_id: str, actor: str, reason: Optional[str] = None) -> DraftModel:
        draft = self.db.query(DraftModel).filter(DraftModel.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")

        draft.status = DraftStatus.REJECTED
        draft.updated_at = datetime.utcnow()

        log = ApprovalLogModel(
            id=f"LOG-{draft_id}-{datetime.utcnow().timestamp()}",
            draft_id=draft_id,
            actor=actor,
            action="REJECTED",
            reason=reason or "Human rejected in approval queue"
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(draft)
        return draft

    def write_draft_to_tracker(self, draft_id: str) -> Dict[str, Any]:
        """Structurally enforce human approval and status floor before writing to tracker."""
        draft = self.db.query(DraftModel).filter(DraftModel.id == draft_id).first()
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")

        # 1. Structural approval check
        if draft.status == DraftStatus.PENDING:
            raise ApprovalRequiredError(
                f"APPROVAL REQUIRED: Draft '{draft_id}' is in PENDING state and has not been approved by a human."
            )

        if draft.status == DraftStatus.REJECTED:
            raise ApprovalRequiredError(
                f"APPROVAL DENIED: Draft '{draft_id}' was REJECTED and cannot be written to external systems."
            )

        if draft.status == DraftStatus.WRITTEN:
            raise AlreadyWrittenError(
                f"IDEMPOTENCY SAFEGUARD: Draft '{draft_id}' has already been written to external tracker."
            )

        payload = json.loads(draft.payload_json)

        # 2. Status Floor & Tag Enforcement (Tab 01 Design Rule)
        tags = payload.get("tags", [])
        if "AI-drafted" not in tags:
            tags.append("AI-drafted")

        # Force status floor to NOT_READY regardless of what LLM payload attempted to set
        enforced_status = "NOT_READY"

        # 3. Perform write to MockTracker adapter
        tracker_record = self.tracker.create_item(
            payload=payload,
            tags=tags,
            status=enforced_status
        )

        # 4. Mark draft as WRITTEN and store write audit record
        draft.status = DraftStatus.WRITTEN
        draft.updated_at = datetime.utcnow()

        write_log = WriteLogModel(
            id=f"WLOG-{draft_id}",
            draft_id=draft_id,
            external_item_id=tracker_record["id"],
            target_system="MockTracker",
            tags=json.dumps(tags),
            status=enforced_status
        )
        self.db.add(write_log)
        self.db.commit()

        logger.info(f"Successfully wrote approved draft '{draft_id}' to MockTracker as item '{tracker_record['id']}'")
        return tracker_record

    def get_pending_drafts(self) -> List[DraftModel]:
        return self.db.query(DraftModel).filter(DraftModel.status == DraftStatus.PENDING).all()

    def get_all_drafts(self) -> List[DraftModel]:
        return self.db.query(DraftModel).all()
