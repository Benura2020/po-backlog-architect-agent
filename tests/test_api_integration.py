"""
API Integration Tests — Approval Gate HTTP enforcement.

Proves the approval gate cannot be bypassed at the HTTP level.

Status code contract:
  PENDING  → POST /approval/write-tracker → 403 Forbidden
  REJECTED → POST /approval/write-tracker → 403 Forbidden
  APPROVED → POST /approval/write-tracker → 200 OK  (status=NOT_READY, tag=AI-drafted)
  WRITTEN  → POST /approval/write-tracker → 409 Conflict (idempotency)

Run:
    pytest tests/test_api_integration.py -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.main import app
from app.db.database import get_db


# ─── In-memory DB fixture ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="module")
def test_session(test_db_engine):
    TestSession = sessionmaker(bind=test_db_engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client(test_db_engine):
    """FastAPI TestClient with DB overridden to in-memory SQLite."""
    TestSession = sessionmaker(bind=test_db_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _create_draft(client: TestClient) -> str:
    """Create a draft via /criteria/generate and return its id from /approval/drafts."""
    # Use the criteria endpoint which internally calls ApprovalService.create_draft()
    client.post("/api/criteria/generate", params={
        "story_id": "INT-TEST-001",
        "title": "Integration Test Story",
        "description": "As a tester, I want to validate the gate so that I can confirm governance."
    })
    drafts = client.get("/api/approval/drafts").json()
    assert len(drafts) > 0, "No drafts created"
    return drafts[-1]["id"]   # most recently created


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestApprovalGateHTTP:
    """
    Structural guarantee: the approval gate cannot be bypassed via HTTP.
    Each test is self-contained and creates its own draft.
    """

    def test_pending_draft_write_returns_403(self, client):
        """PENDING draft → POST /write-tracker → 403 Forbidden."""
        draft_id = _create_draft(client)
        resp = client.post("/api/approval/write-tracker", params={"draft_id": draft_id})
        assert resp.status_code == 403, (
            f"Expected 403 for PENDING draft, got {resp.status_code}. "
            f"Body: {resp.text}"
        )
        data = resp.json()
        assert "detail" in data
        assert "approved" in data["detail"].lower() or "pending" in data["detail"].lower()

    def test_rejected_draft_write_returns_403(self, client):
        """REJECTED draft → POST /write-tracker → 403 Forbidden."""
        draft_id = _create_draft(client)

        # Reject the draft
        reject_resp = client.post("/api/approval/reject", params={
            "draft_id": draft_id,
            "actor": "Human PO",
            "reason": "Insufficient acceptance criteria"
        })
        assert reject_resp.status_code == 200

        # Attempt write — must be blocked
        resp = client.post("/api/approval/write-tracker", params={"draft_id": draft_id})
        assert resp.status_code == 403, (
            f"Expected 403 for REJECTED draft, got {resp.status_code}. "
            f"Body: {resp.text}"
        )

    def test_approved_draft_write_returns_200(self, client):
        """APPROVED draft → POST /write-tracker → 200 OK with NOT_READY status and AI-drafted tag."""
        draft_id = _create_draft(client)

        # Approve the draft
        approve_resp = client.post("/api/approval/approve", params={
            "draft_id": draft_id,
            "actor": "Human PO",
            "reason": "Approved for integration test"
        })
        assert approve_resp.status_code == 200

        # Write tracker — must succeed
        resp = client.post("/api/approval/write-tracker", params={"draft_id": draft_id})
        assert resp.status_code == 200, (
            f"Expected 200 for APPROVED draft, got {resp.status_code}. "
            f"Body: {resp.text}"
        )
        data = resp.json()
        assert data["status"] == "success"

        # Verify NOT_READY status floor
        record = data.get("record", {})
        assert record.get("status") == "NOT_READY", (
            f"Status floor violated — expected NOT_READY, got '{record.get('status')}'"
        )

        # Verify AI-drafted tag
        assert "AI-drafted" in record.get("tags", []), (
            f"AI-drafted tag missing from record. Tags: {record.get('tags')}"
        )

    def test_written_draft_duplicate_write_returns_409(self, client):
        """WRITTEN draft → second POST /write-tracker → 409 Conflict (idempotency)."""
        draft_id = _create_draft(client)

        # Approve and write once
        client.post("/api/approval/approve", params={"draft_id": draft_id, "actor": "Human PO"})
        first_write = client.post("/api/approval/write-tracker", params={"draft_id": draft_id})
        assert first_write.status_code == 200

        # Attempt second write — must return 409
        resp = client.post("/api/approval/write-tracker", params={"draft_id": draft_id})
        assert resp.status_code == 409, (
            f"Expected 409 for duplicate WRITTEN draft write, got {resp.status_code}. "
            f"Body: {resp.text}"
        )

    def test_full_state_machine_sequence(self, client):
        """Full state machine: PENDING → reject → re-create → approve → write → duplicate blocked."""
        # Step 1: Create and verify PENDING
        draft_id = _create_draft(client)

        # Step 2: Attempt write on PENDING → 403
        r = client.post("/api/approval/write-tracker", params={"draft_id": draft_id})
        assert r.status_code == 403, f"Step 2 failed: {r.status_code}"

        # Step 3: Reject
        client.post("/api/approval/reject", params={"draft_id": draft_id, "actor": "Human PO", "reason": "test"})

        # Step 4: Attempt write on REJECTED → 403
        r = client.post("/api/approval/write-tracker", params={"draft_id": draft_id})
        assert r.status_code == 403, f"Step 4 failed: {r.status_code}"

        # Step 5: Create new draft, approve, write → 200
        draft_id2 = _create_draft(client)
        client.post("/api/approval/approve", params={"draft_id": draft_id2, "actor": "Human PO"})
        r = client.post("/api/approval/write-tracker", params={"draft_id": draft_id2})
        assert r.status_code == 200, f"Step 5 failed: {r.status_code}"

        record = r.json().get("record", {})
        assert record.get("status") == "NOT_READY"
        assert "AI-drafted" in record.get("tags", [])

        # Step 6: Duplicate write → 409
        r = client.post("/api/approval/write-tracker", params={"draft_id": draft_id2})
        assert r.status_code == 409, f"Step 6 failed: {r.status_code}"
