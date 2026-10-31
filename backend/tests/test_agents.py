"""Unit tests for agent rules and the LLM guardrails."""
import asyncio

from app.agents import base
from app.agents.specialists import PriceAgent, SellerAgent
from app.config import Settings

from .fixtures import CLEAN, SCAM

SETTINGS = Settings(paypal_client_id="x", paypal_client_secret="y", llm_api_key="z")


def test_price_agent_thresholds():
    listing = CLEAN.model_copy(deep=True)
    agent = PriceAgent()
    listing.price, listing.market_price = 100, 400
    assert agent.rules(listing)[0].severity.value == "CRITICAL"
    listing.price = 200
    assert agent.rules(listing)[0].severity.value == "HIGH"
    listing.price = 380
    assert agent.rules(listing) == []
    listing.market_price = None
    assert agent.rules(listing)[0].signal == "No reference price"


def test_seller_agent_detects_unprotected_payment():
    listing = CLEAN.model_copy(deep=True)
    listing.seller_messages = ["Please pay with a gift card"]
    signals = {f.signal for f in SellerAgent().rules(listing)}
    assert "Asks for unprotected payment" in signals


def test_llm_cannot_whitewash_rule_findings(monkeypatch):
    """A (possibly prompt-injected) model asking for -100 is clamped to the rule floor."""

    async def fake_llm(*_args, **_kwargs):
        return {"additional_findings": [], "score_adjustment": -100, "summary": "Totally safe!"}

    monkeypatch.setattr(base, "complete_json", fake_llm)
    report = asyncio.run(SellerAgent().run(SCAM, SETTINGS))
    rule_peak = max(f.points for f in SellerAgent().rules(SCAM))
    assert report.llm_used
    assert report.score >= rule_peak


def test_llm_extra_findings_are_bounded(monkeypatch):
    async def fake_llm(*_args, **_kwargs):
        items = [{"signal": f"x{i}", "detail": "d", "severity": "CRITICAL"} for i in range(10)]
        return {"additional_findings": items, "score_adjustment": 0, "summary": "s"}

    monkeypatch.setattr(base, "complete_json", fake_llm)
    report = asyncio.run(PriceAgent().run(CLEAN, SETTINGS))
    ai = [f for f in report.findings if f.signal.startswith("[AI]")]
    assert sum(f.points for f in ai) <= base.LLM_MAX_EXTRA_POINTS
