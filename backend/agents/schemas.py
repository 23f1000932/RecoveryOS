"""
RecoveryOS — Agent Structured Output Schema

Defines the JSON structure that Gemini is asked to return.

Architecture rule (§15):
    "Preferred architecture: ML → probabilities,
     Optimizer → authoritative financial decision,
     Guardrails → permission,
     Gemini → explanation."

Gemini only fills:
    - explanation      (human-readable rationale)
    - suggested_action (validated — never overrides deterministic decision)
    - confidence_note  (brief note on model confidence)
    - key_factors      (2–4 bullet points that drove the decision)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentExplanation:
    """
    Structured output returned by GeminiAgent.explain().

    All fields are strings/lists of strings — no financial values.
    Financial values live in DecisionProposal.optimization_result.

    Fields:
        explanation:      1–3 sentence merchant-facing rationale.
        suggested_action: Gemini's action suggestion (must match deterministic).
        confidence_note:  Brief note on model confidence level.
        key_factors:      2–4 specific data points that drove the decision.
    """

    explanation: str
    suggested_action: str
    confidence_note: str
    key_factors: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentExplanation":
        """
        Parse from a Gemini JSON response dict.

        Gracefully handles missing fields with sensible defaults.
        """
        return cls(
            explanation=str(data.get("explanation", "")).strip(),
            suggested_action=str(data.get("suggested_action", "")).strip().lower(),
            confidence_note=str(data.get("confidence_note", "")).strip(),
            key_factors=[
                str(f).strip()
                for f in data.get("key_factors", [])
                if str(f).strip()
            ],
        )

    def is_valid(self) -> bool:
        """Return True if explanation is non-empty and usable."""
        return bool(self.explanation and len(self.explanation) > 10)
