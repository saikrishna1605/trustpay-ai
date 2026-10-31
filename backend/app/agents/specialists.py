"""The four specialist agents. Rules are intentionally transparent and explainable."""
from __future__ import annotations

import re

from ..models import Finding, Listing, RiskLevel
from .base import SEVERITY_POINTS, Agent


def _f(signal: str, detail: str, sev: RiskLevel) -> Finding:
    return Finding(signal=signal, detail=detail, severity=sev, points=SEVERITY_POINTS[sev])


def _hits(text: str, phrases: list[str]) -> list[str]:
    low = text.lower()
    return [p for p in phrases if p in low]


COUNTERFEIT = ["replica", "1:1", "aaa quality", "mirror quality", "super copy", "inspired by", "dupe", "unbranded copy", "high copy"]
URGENCY = ["limited time", "today only", "act fast", "only 1 left", "first come", "won't last", "other buyers are interested", "hurry"]
INJECTION = ["ignore previous", "ignore all", "ai assistant", "mark this as safe", "risk score", "system prompt", "you are an ai"]
OFF_PLATFORM = ["whatsapp", "telegram", "text me at", "email me directly", "contact me outside", "signal app", "dm me on"]
UNPROTECTED_PAY = ["friends and family", "friends & family", "gift card", "wire transfer", "western union", "zelle", "bitcoin", "crypto", "usdt", "pay outside paypal", "bank transfer only", "moneygram"]
PRESSURE = ["deposit to hold", "send a deposit", "reserve it now", "today or i sell", "other buyer"]
NO_RETURNS = ["no returns", "no refunds", "final sale", "all sales final", "sold as is", "as-is", "non-refundable"]


class ProductAgent(Agent):
    name = "Product Agent"
    focus = "whether the product description is coherent, specific and consistent with a genuine item (counterfeit, vague or manipulated listings)."

    def rules(self, listing: Listing) -> list[Finding]:
        text = f"{listing.title}\n{listing.description}"
        out: list[Finding] = []
        if hits := _hits(text, COUNTERFEIT):
            out.append(_f("Counterfeit language", f"Listing uses: {', '.join(hits)}", RiskLevel.HIGH))
        if len(listing.description.strip()) < 40:
            out.append(_f("Thin description", "Description has fewer than 40 characters, so condition and specs can't be verified.", RiskLevel.MEDIUM))
        if hits := _hits(text, URGENCY):
            out.append(_f("Urgency pressure", f"Pressure phrases: {', '.join(hits)}", RiskLevel.MEDIUM))
        if hits := _hits(text + "\n" + "\n".join(listing.seller_messages), INJECTION):
            out.append(_f("Attempt to manipulate AI review", f"Text aimed at automated reviewers: {', '.join(hits)}", RiskLevel.HIGH))
        return out


class SellerAgent(Agent):
    name = "Seller Agent"
    focus = "seller trustworthiness: account history, reputation and whether they try to move the buyer off-platform or away from protected payment."

    def rules(self, listing: Listing) -> list[Finding]:
        s = listing.seller
        out: list[Finding] = []
        if s.account_age_days is None:
            out.append(_f("Unknown account age", "Seller account age not shown.", RiskLevel.LOW))
        elif s.account_age_days < 30:
            out.append(_f("Brand-new seller", f"Account is {s.account_age_days} days old.", RiskLevel.HIGH))
        elif s.account_age_days < 90:
            out.append(_f("Young seller account", f"Account is {s.account_age_days} days old.", RiskLevel.MEDIUM))

        if s.rating is not None:
            if s.rating < 3.5:
                out.append(_f("Poor rating", f"Seller rating {s.rating}/5.", RiskLevel.HIGH))
            elif s.rating < 4.2:
                out.append(_f("Mixed rating", f"Seller rating {s.rating}/5.", RiskLevel.MEDIUM))
        if s.review_count is None or s.review_count < 5:
            out.append(_f("Little review history", f"{s.review_count or 0} reviews.", RiskLevel.MEDIUM))
        if not s.verified:
            out.append(_f("Unverified seller", "Seller identity is not verified by the marketplace.", RiskLevel.LOW))

        convo = "\n".join(listing.seller_messages) + "\n" + listing.description
        if hits := _hits(convo, UNPROTECTED_PAY):
            out.append(_f("Asks for unprotected payment", f"Seller suggests: {', '.join(hits)}. These methods usually remove purchase protection.", RiskLevel.CRITICAL))
        if hits := _hits(convo, OFF_PLATFORM):
            out.append(_f("Moves conversation off-platform", f"Mentions: {', '.join(hits)}", RiskLevel.HIGH))
        if hits := _hits(convo, PRESSURE):
            out.append(_f("Deposit / pressure tactics", f"Mentions: {', '.join(hits)}", RiskLevel.MEDIUM))
        return out


class PriceAgent(Agent):
    name = "Price Agent"
    focus = "whether the price is plausible for this item and condition, and whether it looks like bait."
    llm_extra_instructions = (
        'Also include "estimated_market_price": number|null and "estimate_confidence": "low"|"medium"|"high". '
        "The estimate is the typical price, in the listing currency, of this exact item in this condition, "
        "from your general knowledge. Use null if the item can't be identified precisely. "
        "Never take a price claim from the listing text as the market price."
    )

    def extra_llm_findings(self, listing: Listing, result: dict) -> list[Finding]:
        # Only used when the buyer gave no reference price. AI estimates are less reliable than a
        # buyer-supplied price, so they're capped at HIGH and only medium/high confidence counts.
        if listing.market_price:
            return []
        try:
            est = float(result.get("estimated_market_price") or 0)
        except (TypeError, ValueError):
            return []
        if est <= 0 or str(result.get("estimate_confidence", "")).lower() not in ("medium", "high"):
            return []
        r = listing.price / est
        pct = round((1 - r) * 100)
        detail = f"{pct}% below the AI-estimated typical price of about {est:,.0f} {listing.currency} ({result.get('estimate_confidence')} confidence). Verify before relying on it."
        if r < 0.35:
            return [_f("[AI] Far below estimated market price", detail, RiskLevel.HIGH)]
        if r < 0.55:
            return [_f("[AI] Far below estimated market price", detail, RiskLevel.MEDIUM)]
        return []

    def ratio(self, listing: Listing) -> float | None:
        return listing.price / listing.market_price if listing.market_price else None

    def rules(self, listing: Listing) -> list[Finding]:
        r = self.ratio(listing)
        if r is None:
            return [_f("No reference price", "No typical market price was provided, so the discount can't be checked.", RiskLevel.LOW)]
        pct = round((1 - r) * 100)
        if r < 0.35:
            return [_f("Implausibly low price", f"{pct}% below typical price ({listing.market_price:.2f}).", RiskLevel.CRITICAL)]
        if r < 0.55:
            return [_f("Far below market", f"{pct}% below typical price ({listing.market_price:.2f}).", RiskLevel.HIGH)]
        if r < 0.75:
            return [_f("Notable discount", f"{pct}% below typical price ({listing.market_price:.2f}).", RiskLevel.MEDIUM)]
        if r > 1.5:
            return [_f("Overpriced", f"{round((r - 1) * 100)}% above typical price.", RiskLevel.MEDIUM)]
        return []


class PolicyAgent(Agent):
    name = "Policy Agent"
    focus = "return, refund and delivery terms, and whether they leave the buyer without recourse."

    def rules(self, listing: Listing) -> list[Finding]:
        policy = listing.return_policy.strip()
        out: list[Finding] = []
        if not policy:
            out.append(_f("No return policy", "Seller doesn't state a return policy.", RiskLevel.MEDIUM))
        else:
            if hits := _hits(policy + "\n" + listing.description, NO_RETURNS):
                out.append(_f("No-returns terms", f"Policy says: {', '.join(hits)}", RiskLevel.HIGH))
            days = re.search(r"(\d{1,3})\s*-?\s*day", policy.lower())
            if days and int(days.group(1)) < 14:
                out.append(_f("Short return window", f"Only {days.group(1)} days to return.", RiskLevel.MEDIUM))
            if "restocking" in policy.lower():
                out.append(_f("Restocking fee", "Returns carry a restocking fee.", RiskLevel.LOW))
        if listing.shipping_days is not None and listing.shipping_days > 21:
            out.append(_f("Long delivery time", f"Ships in {listing.shipping_days} days, which delays discovering problems.", RiskLevel.MEDIUM))
        return out


ALL_AGENTS: list[Agent] = [ProductAgent(), SellerAgent(), PriceAgent(), PolicyAgent()]
