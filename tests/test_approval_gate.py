import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.services.approval_service import ApprovalService, ApprovalRequiredError, AlreadyWrittenError
from app.adapters.tracker import MockTracker
from app.schemas.domain import DraftStatus


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_approval_gate_prevents_unapproved_writes(db_session):
    tracker = MockTracker()
    service = ApprovalService(db_session, tracker)

    # 1. Create a PENDING draft
    draft = service.create_draft("STORY", "Test Pending Story", {
        "id": "ST-PENDING-01",
        "title": "Test Pending Story",
        "description": "As a user..."
    })
    assert draft.status == DraftStatus.PENDING

    # 2. Attempt write on PENDING draft -> MUST raise ApprovalRequiredError
    with pytest.raises(ApprovalRequiredError):
        service.write_draft_to_tracker(draft.id)

    # 3. Reject draft
    service.reject_draft(draft.id, "Human PO", "Lacks user value")
    assert draft.status == DraftStatus.REJECTED

    # 4. Attempt write on REJECTED draft -> MUST raise ApprovalRequiredError
    with pytest.raises(ApprovalRequiredError):
        service.write_draft_to_tracker(draft.id)

    # 5. Create and Approve a second draft
    draft2 = service.create_draft("STORY", "Test Approved Story", {
        "id": "ST-APPROVED-01",
        "title": "Test Approved Story",
        "description": "As a user..."
    })
    service.approve_draft(draft2.id, "Human PO")
    assert draft2.status == DraftStatus.APPROVED

    # 6. Perform write on APPROVED draft -> MUST succeed
    record = service.write_draft_to_tracker(draft2.id)
    assert record is not None
    assert record["status"] == "NOT_READY"  # Status floor enforced
    assert "AI-drafted" in record["tags"]  # Tagged AI-drafted

    # 7. Attempt duplicate write on WRITTEN draft -> MUST raise AlreadyWrittenError (Idempotency)
    with pytest.raises(AlreadyWrittenError):
        service.write_draft_to_tracker(draft2.id)
