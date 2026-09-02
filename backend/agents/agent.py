"""
RecoveryOS — Gemini Agent

Async, stateless explanation agent. Wraps the Google Gemini API.

Architecture rules (§16, §17):
  - The agent is read-only. It NEVER calls execution tools.
  - It NEVER changes DecisionProposal financial values.
  - It NEVER raises. Returns None on any failure.
  - The pipeline falls back to the template explanation on None (Rule 4).

Usage:
    agent = GeminiAgent(api_key="...", model="gemini-2.5-flash")
    result = await agent.explain(proposal, context)
    if result is not None:
        explanation = result.explanation
    else:
        explanation = template_fallback

Threading:
    Stateless after construction. Safe for concurrent use.
    Constructed once at startup via create_pipeline() or app lifespan.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from backend.agents.prompts import SYSTEM_PROMPT, build_user_message
from backend.agents.schemas import AgentExplanation

if TYPE_CHECKING:
    from backend.orchestrator.context import CaseContext, DecisionProposal

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_DEFAULT_TIMEOUT = 10.0   # seconds — generous enough for flash, tight enough for latency


class GeminiAgent:
    """
    Async, stateless Gemini explanation agent.

    Wraps google-generativeai. Returns AgentExplanation on success,
    None on any failure (timeout, API error, JSON parse error, validation error).

    Args:
        api_key: Google Gemini API key.
        model:   Gemini model name. Default: gemini-2.5-flash.
        timeout: API call timeout in seconds. Default: 10.0.
    """

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key:
            raise ValueError("GeminiAgent: api_key must be non-empty.")

        self._api_key = api_key
        self._model_name = model
        self._timeout = timeout
        self._client = None   # lazy-initialised on first call

        logger.info("GeminiAgent initialised: model=%s timeout=%.1fs", model, timeout)

    def _get_client(self):
        """Lazy-initialise the google-genai Client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except ImportError:
                logger.error(
                    "GeminiAgent: google-genai is not installed. "
                    "Run: pip install google-genai"
                )
                raise
        return self._client

    async def explain(
        self,
        proposal: DecisionProposal,
        context: CaseContext,
    ) -> AgentExplanation | None:
        """
        Generate a merchant-facing explanation for a recovery decision.

        Never raises. Returns None on any failure.
        The pipeline falls back to the Phase 3 template explanation on None.

        Args:
            proposal: DecisionProposal from the deterministic pipeline.
            context:  CaseContext for this case.

        Returns:
            AgentExplanation on success, None on any failure.
        """
        try:
            return await asyncio.wait_for(
                self._call_gemini(proposal, context),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "GeminiAgent: timeout after %.1fs for case %s — using template fallback.",
                self._timeout, context.case_id,
            )
            return None
        except Exception as exc:
            logger.warning(
                "GeminiAgent: unexpected error for case %s: %s — using template fallback.",
                context.case_id, exc,
            )
            return None

    async def _call_gemini(
        self,
        proposal: DecisionProposal,
        context: CaseContext,
    ) -> AgentExplanation | None:
        """
        Inner async method: build prompt → call Gemini → parse → validate.

        Separated from explain() so asyncio.wait_for() can cancel it cleanly.
        """
        from google import genai
        from google.genai import types

        user_message = build_user_message(proposal, context)

        # Run the synchronous google-genai SDK call in a thread executor
        loop = asyncio.get_event_loop()
        client = self._get_client()

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.3,
            max_output_tokens=512,
        )

        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=self._model_name,
                contents=user_message,
                config=config,
            ),
        )

        raw_text = response.text.strip()
        if not raw_text:
            logger.warning(
                "GeminiAgent: empty response for case %s.", context.case_id
            )
            return None

        # Parse JSON
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning(
                "GeminiAgent: JSON parse error for case %s: %s\nRaw: %.200s",
                context.case_id, exc, raw_text,
            )
            return None

        explanation = AgentExplanation.from_dict(data)

        if not explanation.is_valid():
            logger.warning(
                "GeminiAgent: explanation is empty or too short for case %s.",
                context.case_id,
            )
            return None

        # ── Safety check (§15) — validate suggested_action ────────────────────
        # Gemini must not override the deterministic decision.
        deterministic_action = proposal.recommended_action.value
        if explanation.suggested_action != deterministic_action:
            logger.warning(
                "GeminiAgent: suggested_action mismatch for case %s — "
                "Gemini=%r, deterministic=%r. Keeping deterministic.",
                context.case_id,
                explanation.suggested_action,
                deterministic_action,
            )
            # Keep the explanation text (it may still be useful) but correct the field
            explanation.suggested_action = deterministic_action

        logger.info(
            "GeminiAgent: explanation generated for case %s (action=%s, factors=%d).",
            context.case_id,
            explanation.suggested_action,
            len(explanation.key_factors),
        )
        return explanation
