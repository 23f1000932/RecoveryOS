"""
RecoveryOS — Action Adapter Package

Public API:
    ActionResult      — structured result returned by every adapter
    VerificationResult — returned by VerificationAdapter
    get_adapter()     — factory: returns the correct adapter for an ActionType
"""

from backend.tools.protocol import ActionResult, VerificationResult

__all__ = ["ActionResult", "VerificationResult"]
