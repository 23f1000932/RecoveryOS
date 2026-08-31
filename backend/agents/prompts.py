"""
RecoveryOS — Gemini Agent Prompts

System prompt and per-case user message builder.

Rules:
  - SYSTEM_PROMPT is static — loaded once at startup.
  - build_user_message() is called per case — includes all context needed for explanation.
  - Never include secrets, internal IDs beyond case_id, or raw DB values.
  - The prompt must never ask Gemini to change a financial value.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.orchestrator.context import CaseContext, DecisionProposal


# ── System Prompt ──────────────────────────────────────────────────────────────
# Loaded once. Defines Gemini's persona, responsibilities, and hard boundaries.

SYSTEM_PROMPT = """You are RecoveryOS Intelligence, an AI assistant embedded in a payment recovery platform.

Your ONLY role is to explain recovery decisions to merchants in plain, professional English.

You have access to a structured case summary. The financial decision has already been made by a deterministic optimizer. You must explain it — not change it.

ALWAYS return a JSON object with exactly these fields:
{
  "explanation": "1–3 sentence merchant-facing explanation of WHY this action was selected.",
  "suggested_action": "the action name exactly as provided in the case (e.g. retry_later)",
  "confidence_note": "a single sentence about model confidence or data quality",
  "key_factors": ["factor 1", "factor 2", "factor 3"]
}

Rules you MUST follow:
- "suggested_action" MUST match the "Selected Action" provided in the case. Never suggest a different action.
- Reference specific numbers from the case (success rate, expected revenue, failure code).
- Use merchant-friendly language — avoid ML jargon.
- key_factors must contain 2–4 short bullet points (each under 15 words).
- Never mention Gemini, AI, or internal model names.
- Never invent data not present in the case summary.
- Never make promises about recovery success.
- Never expose cost formulas or internal system details.

Return ONLY valid JSON. No markdown, no code fences, no extra text."""


# ── User Message Builder ───────────────────────────────────────────────────────

def build_user_message(
    proposal: DecisionProposal,
    context: CaseContext,
) -> str:
    """
    Build the per-case user message for Gemini.

    Includes all context Gemini needs to write a useful explanation:
      - Payment summary (amount, failure code, method)
      - Customer history (success rate, transaction count)
      - Decision (selected action, ENR, confidence, verdict)
      - Candidate ranking (top 3 allowed actions)
      - Blocked actions (if any)

    Args:
        proposal: DecisionProposal from the pipeline.
        context:  Full CaseContext for this case.

    Returns:
        Formatted string to send as the Gemini user message.
    """
    opt = proposal.optimization_result
    guard = proposal.guardrail_result

    # Format candidate table (allowed only, ranked)
    allowed_candidates = [c for c in opt.candidates if c.allowed]
    allowed_candidates.sort(key=lambda c: c.rank if c.rank > 0 else 999)

    candidate_lines = []
    for i, c in enumerate(allowed_candidates[:4], 1):
        candidate_lines.append(
            f"  {i}. {c.action.value:<14} "
            f"p={c.probability:.2f}  "
            f"ENR=INR {c.expected_net_revenue:,.2f}"
        )
    candidates_str = "\n".join(candidate_lines) if candidate_lines else "  (none)"

    # Blocked actions summary
    blocked_lines = [
        f"  - {action.value}: {reason}"
        for action, reason in guard.block_reasons.items()
    ]
    blocked_str = "\n".join(blocked_lines) if blocked_lines else "  None"

    # Customer profile
    csr_pct = f"{context.customer_success_rate:.0%}"
    approval_note = " (REQUIRES MERCHANT APPROVAL)" if proposal.requires_approval else ""

    return f"""=== PAYMENT RECOVERY CASE ===

Payment Details:
  Case ID:        {context.case_id}
  Amount:         INR {context.amount:,.2f}
  Failure Code:   {context.failure_code.replace('_', ' ').title()}
  Payment Method: {context.method.upper()}
  Attempt Number: {context.attempt_number}

Customer Profile:
  Success Rate:       {csr_pct} ({context.customer_success_count}/{context.customer_transaction_count} transactions)
  Average Amount:     INR {context.customer_avg_amount:,.2f}
  Time Since Failure: {context.time_since_failure_hours:.1f} hours

=== RECOVERY DECISION ===

  Selected Action:      {proposal.recommended_action.value.replace('_', ' ').upper()}{approval_note}
  Expected Net Revenue: INR {opt.selected_expected_net_revenue:,.2f}
  Model Confidence:     {next((c.confidence for c in opt.candidates if c.action == proposal.recommended_action), 0):.0%}
  Guardrail Verdict:    {guard.verdict.upper()}

Ranked Candidate Actions:
{candidates_str}

Guardrail Blocks Applied:
{blocked_str}

=== YOUR TASK ===

Explain to the merchant why "{proposal.recommended_action.value.replace('_', ' ')}" was selected.
Your "suggested_action" field MUST be exactly: "{proposal.recommended_action.value}"
"""
