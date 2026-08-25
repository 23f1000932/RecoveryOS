"""
RecoveryOS — Recovery Cases API

GET  /api/recovery-cases
GET  /api/recovery-cases/{case_id}
POST /api/recovery-cases/{case_id}/analyze
POST /api/recovery-cases/{case_id}/approve
POST /api/recovery-cases/{case_id}/reject
POST /api/recovery-cases/{case_id}/execute
POST /api/recovery-cases/{case_id}/stop
GET  /api/recovery-cases/{case_id}/audit
"""

import logging
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query

from backend.db.repositories.audit import AuditRepository
from backend.db.repositories.recovery_cases import RecoveryCaseRepository
from backend.domain.enums import ApprovalStatus, CaseStatus
from backend.domain.schemas import (
    ApprovalRequest,
    ApprovalResponse,
    AuditLogEntry,
    AuditLogResponse,
    ExecuteRequest,
    ExecuteResponse,
    RecoveryCaseDetail,
    RecoveryCaseListResponse,
    RecoveryCaseSummary,
    StopResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recovery-cases", tags=["Recovery Cases"])

MERCHANT_ID = "00000000-0000-0000-0000-000000000001"


def _fmt(value) -> str | None:
    if value is None:
        return None
    return f"{Decimal(str(value)):.2f}"


@router.get("", response_model=RecoveryCaseListResponse)
async def list_recovery_cases(
    status: str | None = Query(None, description="Filter by case status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> RecoveryCaseListResponse:
    """List recovery cases with optional status filter."""
    try:
        repo = RecoveryCaseRepository()
        cases_data, total = await repo.list_cases(
            merchant_id=MERCHANT_ID,
            status=status,
            page=page,
            page_size=page_size,
        )
        cases = [_row_to_summary(r) for r in cases_data]
        return RecoveryCaseListResponse(
            cases=cases,
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        logger.error("list_recovery_cases error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list recovery cases")


@router.get("/{case_id}", response_model=RecoveryCaseDetail)
async def get_recovery_case(case_id: str) -> RecoveryCaseDetail:
    """Get full case detail including candidates and guardrail results."""
    repo = RecoveryCaseRepository()
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    candidates_data = await repo.get_action_candidates(case_id)

    from backend.domain.schemas import ActionCandidateSchema, GuardrailResultSchema
    from backend.domain.enums import ActionType, GuardrailOutcome

    candidates = [
        ActionCandidateSchema(
            action=ActionType(c["action"]),
            probability=float(c["probability"]),
            confidence=float(c["model_confidence"]),
            model_name=case.get("model_name") or "rule_based",
            model_version=case.get("model_version") or "v1",
            recoverable_amount=_fmt(c["recoverable_amount"]),
            intervention_cost=_fmt(c["intervention_cost"]),
            incentive_cost=_fmt(c["incentive_cost"]),
            contact_cost=_fmt(c["contact_cost"]),
            expected_gross_recovery=_fmt(c["expected_gross_recovery"]),
            expected_net_revenue=_fmt(c["expected_net_revenue"]),
            allowed=c["allowed"],
            blocked_reason=c.get("blocked_reason"),
            rank=c["rank"],
        )
        for c in candidates_data
    ]

    # Load payment and customer data for full detail
    from backend.db.repositories.payments import PaymentsRepository
    from backend.db.repositories.customers import CustomersRepository
    pay_repo = PaymentsRepository()
    cust_repo = CustomersRepository()
    payment = await pay_repo.get_payment(str(case["payment_id"]))
    customer = await cust_repo.get_customer(str(case["customer_id"]))

    payment = payment or {}
    customer = customer or {}
    success_rate = 0.0
    tx_count = customer.get("transaction_count", 0)
    if tx_count > 0:
        success_rate = customer.get("success_count", 0) / tx_count

    return RecoveryCaseDetail(
        id=str(case["id"]),
        payment_id=str(case["payment_id"]),
        customer_id=str(case["customer_id"]),
        merchant_id=str(case["merchant_id"]),
        status=CaseStatus(case["status"]),
        payment_amount=_fmt(payment.get("amount", 0)),
        payment_currency=payment.get("currency", "INR"),
        payment_method=payment.get("method", "unknown"),
        payment_failure_code=payment.get("failure_code", "unknown"),
        payment_attempt_number=payment.get("attempt_number", 1),
        external_payment_id=payment.get("external_payment_id", ""),
        customer_transaction_count=customer.get("transaction_count", 0),
        customer_success_count=customer.get("success_count", 0),
        customer_failure_count=customer.get("failure_count", 0),
        customer_success_rate=round(success_rate, 4),
        customer_avg_amount=_fmt(customer.get("avg_amount", 0)),
        customer_preferred_method=customer.get("preferred_method", "card"),
        revenue_at_risk=_fmt(case.get("revenue_at_risk")),
        selected_action=case.get("selected_action"),
        expected_gross_recovery=_fmt(case.get("expected_gross_recovery")),
        expected_net_revenue=_fmt(case.get("expected_net_revenue")),
        actual_recovered=_fmt(case.get("actual_recovered")),
        intervention_cost=_fmt(case.get("intervention_cost")),
        incremental_recovery=_fmt(case.get("incremental_recovery")),
        net_incremental_recovery=_fmt(case.get("net_incremental_recovery")),
        requires_approval=bool(case.get("requires_approval", False)),
        approval_status=ApprovalStatus(case.get("approval_status", "not_required")),
        model_name=case.get("model_name"),
        model_version=case.get("model_version"),
        policy_version=case.get("policy_version"),
        candidates=candidates,
        guardrail_result=None,   # Loaded from audit in Phase 7
        agent_explanation=None,  # Loaded from audit in Phase 9
        expires_at=case.get("expires_at"),
        created_at=case["created_at"],
        updated_at=case["updated_at"],
    )


@router.post("/{case_id}/analyze")
async def analyze_case(case_id: str) -> dict:
    """
    Trigger analysis pipeline for a case.
    Runs Detect → Contextualize → Predict → Optimize → Guard.
    Does NOT execute a money-moving action.
    Wired to RecoveryPipeline in Phase 7.
    """
    # Phase 1 stub — returns not-yet-implemented message
    return {
        "case_id": case_id,
        "status": "not_implemented",
        "message": "Analysis pipeline will be wired in Phase 7.",
    }


@router.post("/{case_id}/approve", response_model=ApprovalResponse)
async def approve_case(case_id: str, body: ApprovalRequest) -> ApprovalResponse:
    """Approve a case that is in PENDING_APPROVAL state."""
    repo = RecoveryCaseRepository()
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    current_status = CaseStatus(case["status"])
    if current_status != CaseStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CASE_NOT_PENDING_APPROVAL",
                    "message": f"Case is in state {current_status.value}, not PENDING_APPROVAL.",
                    "details": {},
                }
            },
        )

    await repo.update_approval(
        case_id=case_id,
        approval_status=ApprovalStatus.APPROVED,
        case_status=CaseStatus.APPROVED,
    )

    return ApprovalResponse(
        case_id=case_id,
        approval_status=ApprovalStatus.APPROVED,
        case_status=CaseStatus.APPROVED,
        message="Case approved for execution.",
    )


@router.post("/{case_id}/reject", response_model=ApprovalResponse)
async def reject_case(case_id: str, body: ApprovalRequest) -> ApprovalResponse:
    """Reject a case that is in PENDING_APPROVAL state."""
    repo = RecoveryCaseRepository()
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    current_status = CaseStatus(case["status"])
    if current_status != CaseStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CASE_NOT_PENDING_APPROVAL",
                    "message": f"Case is in state {current_status.value}, not PENDING_APPROVAL.",
                    "details": {},
                }
            },
        )

    await repo.update_approval(
        case_id=case_id,
        approval_status=ApprovalStatus.REJECTED,
        case_status=CaseStatus.STOPPED,
    )

    return ApprovalResponse(
        case_id=case_id,
        approval_status=ApprovalStatus.REJECTED,
        case_status=CaseStatus.STOPPED,
        message="Case rejected. Recovery stopped.",
    )


@router.post("/{case_id}/execute", response_model=ExecuteResponse)
async def execute_case(case_id: str, body: ExecuteRequest) -> ExecuteResponse:
    """
    Execute the approved recovery action.
    Backend validates status — frontend cannot override this check.
    Wired to RecoveryPipeline in Phase 7.
    """
    repo = RecoveryCaseRepository()
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    current_status = CaseStatus(case["status"])
    requires_approval = bool(case.get("requires_approval", False))

    executable = (
        current_status == CaseStatus.APPROVED
        or (current_status == CaseStatus.DECISION_READY and not requires_approval)
    )

    if not executable:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CASE_NOT_EXECUTABLE",
                    "message": f"Case is in state {current_status.value} and cannot be executed.",
                    "details": {"requires_approval": requires_approval},
                }
            },
        )

    # Phase 1 stub — full execution wired in Phase 7
    return ExecuteResponse(
        case_id=case_id,
        case_status=current_status,
        action_executed=None,
        actual_recovered=None,
        message="Execution pipeline will be wired in Phase 7.",
    )


@router.post("/{case_id}/stop", response_model=StopResponse)
async def stop_case(case_id: str) -> StopResponse:
    """Manually stop recovery for a case."""
    repo = RecoveryCaseRepository()
    case = await repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    current_status = CaseStatus(case["status"])
    if current_status.is_terminal:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "CASE_ALREADY_TERMINAL",
                    "message": f"Case is already in terminal state {current_status.value}.",
                    "details": {},
                }
            },
        )

    # Atomic transition to STOPPED
    transitioned = await repo.transition_status(
        case_id=case_id,
        from_status=current_status,
        to_status=CaseStatus.STOPPED,
    )
    if not transitioned:
        raise HTTPException(status_code=409, detail="Concurrent state conflict. Retry.")

    return StopResponse(
        case_id=case_id,
        case_status=CaseStatus.STOPPED,
        message="Recovery stopped.",
    )


@router.get("/{case_id}/audit", response_model=AuditLogResponse)
async def get_case_audit(case_id: str) -> AuditLogResponse:
    """Return the full audit timeline for a case."""
    case_repo = RecoveryCaseRepository()
    if not await case_repo.get_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")

    audit_repo = AuditRepository()
    entries_data = await audit_repo.get_case_audit(case_id)

    from backend.domain.enums import AuditEventType, PipelineSource
    entries = []
    for e in entries_data:
        try:
            entries.append(
                AuditLogEntry(
                    id=str(e["id"]),
                    case_id=str(e["case_id"]),
                    event_type=AuditEventType(e["event_type"]),
                    actor=e["actor"],
                    source=e["source"],
                    model_name=e.get("model_name"),
                    model_version=e.get("model_version"),
                    policy_version=e.get("policy_version"),
                    input_snapshot=e.get("input_snapshot") or {},
                    output_snapshot=e.get("output_snapshot") or {},
                    decision=e.get("decision"),
                    guardrail_result=e.get("guardrail_result"),
                    timestamp=e["timestamp"],
                )
            )
        except Exception as exc:
            logger.warning("Skipping malformed audit entry: %s", exc)

    return AuditLogResponse(
        case_id=case_id,
        entries=entries,
        total=len(entries),
    )


def _row_to_summary(row: dict) -> RecoveryCaseSummary:
    from backend.domain.enums import ActionType
    return RecoveryCaseSummary(
        id=str(row["id"]),
        payment_id=str(row["payment_id"]),
        customer_id=str(row["customer_id"]),
        merchant_id=str(row["merchant_id"]),
        status=CaseStatus(row["status"]),
        revenue_at_risk=_fmt(row.get("revenue_at_risk")),
        selected_action=(
            ActionType(row["selected_action"]) if row.get("selected_action") else None
        ),
        expected_net_revenue=_fmt(row.get("expected_net_revenue")),
        model_confidence=None,
        requires_approval=bool(row.get("requires_approval", False)),
        approval_status=ApprovalStatus(row.get("approval_status", "not_required")),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
