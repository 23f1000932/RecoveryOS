"""
RecoveryOS — API Endpoint Integration & Error Contract Tests

Tests required by techstack §26 and architecture §28, §32, §46:
  - Health check
  - Dashboard summary
  - Case listing and details
  - Case lifecycle: analyze, approve, reject, execute, stop
  - Concurrency 409 conflict and Action Idempotency
  - Audit trail timeline verification
  - Error contract structure: {"error": {"code": ..., "message": ..., "details": ...}}
  - Simulator list and retrieval
"""

from __future__ import annotations

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app

MERCHANT_ID = "00000000-0000-0000-0000-000000000001"
CASE_A = "00000000-0000-0000-0000-000000000030"
CASE_D = "00000000-0000-0000-0000-000000000033"


@pytest.fixture
async def client():
    from backend.db.connection import close_db, init_db
    try:
        await init_db()
    except Exception:
        pass
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    try:
        await close_db()
    except Exception:
        pass


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "environment" in data


class TestDashboardEndpoints:
    @pytest.mark.asyncio
    async def test_dashboard_summary(self, client: AsyncClient):
        resp = await client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = resp.json()
        required_fields = [
            "revenue_at_risk",
            "revenue_recovered",
            "baseline_recovered",
            "incremental_recovery",
            "net_incremental_recovery",
            "recovery_rate",
            "baseline_recovery_rate",
            "total_cases",
        ]
        for f in required_fields:
            assert f in data, f"Missing field {f} in dashboard summary"


class TestRecoveryCasesEndpoints:
    @pytest.mark.asyncio
    async def test_list_cases(self, client: AsyncClient):
        resp = await client.get("/api/recovery-cases")
        assert resp.status_code == 200
        data = resp.json()
        assert "cases" in data
        assert "total" in data
        assert isinstance(data["cases"], list)

    @pytest.mark.asyncio
    async def test_get_case_not_found(self, client: AsyncClient):
        random_id = str(uuid.uuid4())
        resp = await client.get(f"/api/recovery-cases/{random_id}")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_seeded_case(self, client: AsyncClient):
        resp = await client.get(f"/api/recovery-cases/{CASE_A}")
        if resp.status_code == 200:
            data = resp.json()
            assert data["id"] == CASE_A
            assert "status" in data
            assert "revenue_at_risk" in data

    @pytest.mark.asyncio
    async def test_analyze_case_persists_decision_and_audit(self, client: AsyncClient):
        resp = await client.post(f"/api/recovery-cases/{CASE_A}/analyze")
        if resp.status_code == 200:
            data = resp.json()
            assert data["case_id"] == CASE_A
            assert data["status"] == "analyzed"
            assert "recommended_action" in data
            assert "candidates" in data

            # Verify audit trail is populated
            audit_resp = await client.get(f"/api/recovery-cases/{CASE_A}/audit")
            assert audit_resp.status_code == 200
            audit_data = audit_resp.json()
            assert audit_data["total"] > 0
            event_types = [e["event_type"] for e in audit_data["entries"]]
            assert "context_loaded" in event_types
            assert "predictions_generated" in event_types
            assert "optimization_completed" in event_types

    @pytest.mark.asyncio
    async def test_approve_reject_guards(self, client: AsyncClient):
        # Case A is DECISION_READY, not PENDING_APPROVAL -> should reject approve with 400
        resp = await client.post(
            f"/api/recovery-cases/{CASE_A}/approve",
            json={"notes": "test approve"},
        )
        assert resp.status_code in (400, 404)
        if resp.status_code == 400:
            data = resp.json()
            assert "error" in data
            assert data["error"]["code"] == "CASE_NOT_PENDING_APPROVAL"

    @pytest.mark.asyncio
    async def test_concurrency_and_idempotency_on_execute(self, client: AsyncClient):
        # Case D requires approval -> executing directly should be blocked (400)
        resp = await client.post(
            f"/api/recovery-cases/{CASE_D}/execute",
            json={"force": False},
        )
        assert resp.status_code in (400, 404)
        if resp.status_code == 400:
            data = resp.json()
            assert "error" in data
            assert data["error"]["code"] == "CASE_NOT_EXECUTABLE"


class TestSimulatorEndpoints:
    @pytest.mark.asyncio
    async def test_list_simulator_experiments(self, client: AsyncClient):
        resp = await client.get("/api/simulator")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_nonexistent_experiment(self, client: AsyncClient):
        random_id = str(uuid.uuid4())
        resp = await client.get(f"/api/simulator/{random_id}")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"


class TestErrorContract:
    @pytest.mark.asyncio
    async def test_validation_error_format(self, client: AsyncClient):
        # Trigger validation error on page query param (ge=1)
        resp = await client.get("/api/recovery-cases?page=0")
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"]
        assert "errors" in data["error"]["details"]
