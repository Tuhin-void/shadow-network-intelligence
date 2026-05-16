"""
Shadow Network Intelligence - Reasoning Package
Risk scoring and explainability.

Note: legacy stub re-exports (.risk_scorer / .fraud_explainer) are wrapped
in try/except so the package remains importable when the stubs are absent
or in mid-refactor. The professional synthesis API lives in
`6_reasoning_engine.synthesis`.
"""
try:
    from .scoring.risk_scorer import RiskScorer  # type: ignore
except Exception:
    RiskScorer = None  # type: ignore
try:
    from .explainability.fraud_explainer import FraudExplainer  # type: ignore
except Exception:
    FraudExplainer = None  # type: ignore

__all__ = ["RiskScorer", "FraudExplainer"]