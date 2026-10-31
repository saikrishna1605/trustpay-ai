"""Channel3 search and a read-only analytics feed for AG Studio.

Product search is evidence for comparison, never independent seller verification.
No product search result can set a PayPal payee or bypass the approval gate.
"""
from datetime import datetime, timezone
from math import isfinite
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=300)
    limit: int = Field(6, ge=1, le=10)
    currency: str = Field("USD", pattern=r"^[A-Z]{3}$")


def web_url(value):
    return value if isinstance(value, str) and urlparse(value).scheme in ("http", "https") else None


def normalize_products(payload):
    # Channel3 responses may wrap product arrays in products/results/data.
    items = payload
    if isinstance(items, dict):
        items = items.get("products", items.get("results", items.get("data", [])))
    if isinstance(items, dict):
        items = items.get("products", items.get("results", []))
    if not isinstance(items, list):
        raise ValueError("Channel3 response has no product array")
    products = []
    for item in items:
        if not isinstance(item, dict):
            continue
        offers = []
        for offer in item.get("offers") or []:
            if not isinstance(offer, dict):
                continue
            price = offer.get("price") or {}
            amount = price.get("price", price.get("amount")) if isinstance(price, dict) else price
            currency = price.get("currency") if isinstance(price, dict) else offer.get("currency")
            try:
                amount = float(amount)
                if not isfinite(amount) or amount <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            merchant = offer.get("merchant", offer.get("seller", "Retailer"))
            if isinstance(merchant, dict):
                merchant = merchant.get("name", "Retailer")
            offers.append({"price": amount, "currency": str(currency or "UNKNOWN").upper(),
                           "url": web_url(offer.get("url")), "merchant": str(merchant)})
        images = item.get("images") or []
        image = images[0] if images else item.get("image_url")
        if isinstance(image, dict):
            image = image.get("url")
        products.append({"id": str(item.get("id", "")), "title": str(item.get("title", item.get("name", "Product"))),
                         "image_url": web_url(image), "offers": offers})
    return products


async def search_channel3(settings, body, transport=None):
    if not settings.channel3_api_key:
        raise HTTPException(503, "Set CHANNEL3_API_KEY on the server to enable product comparisons")
    try:
        async with httpx.AsyncClient(timeout=20, transport=transport) as client:
            response = await client.post(f"{settings.channel3_base_url}/search",
                headers={"x-api-key": settings.channel3_api_key},
                json={"query": body.query, "limit": body.limit})
        if response.status_code == 429:
            raise HTTPException(503, "Channel3 quota or rate limit reached; retry later")
        response.raise_for_status()
        products = normalize_products(response.json())[:body.limit]
    except (httpx.HTTPError, ValueError, TypeError):
        raise HTTPException(502, "Channel3 search unavailable or returned an unsupported response") from None
    return {"provider": "Channel3", "query": body.query,
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "products": products,
            "currency": body.currency,
            "notice": "Comparison candidates, not verified sellers. Check model, condition, shipping and currency. Retailer links do not use TrustPay checkout."}


def sponsor_router(settings, store, require_api_key, rate_limit):
    router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])

    @router.post("/products/search", dependencies=[Depends(rate_limit)])
    async def search(body: SearchRequest):
        return await search_channel3(settings, body)

    @router.get("/sponsors/status")
    def status():
        return {"channel3_configured": bool(settings.channel3_api_key), "ag_studio": "frontend",
                "deployment": "Render Blueprint included"}

    @router.get("/developer/status")
    def developer_status():
        return {"environment": settings.paypal_env, "ai_provider": settings.llm_provider,
                "ai_model": settings.llm_model, "channel3_configured": bool(settings.channel3_api_key),
                "webhook_configured": bool(settings.paypal_webhook_id),
                "api_key_required": bool(settings.api_key), "default_checkout_locale": settings.paypal_locale,
                "supported_locales": ["en-US", "ar-AE", "fr-FR"], "storage": "SQLite"}

    @router.get("/analytics")
    def analytics():
        rows = [{"id": a.id, "created_at": a.created_at, "product": a.listing.title,
                 "seller": a.listing.seller.name, "amount": a.listing.price, "currency": a.listing.currency,
                 "risk_score": a.overall_score, "risk_level": a.risk_level.value,
                 "ai_status": a.ai_status, "decision": a.decision or "pending",
                 "payment_status": a.payment_status or "NOT_STARTED", "checkout_locale": a.checkout_locale,
                 "order_id": a.paypal_order_id, "capture_id": a.capture_id} for a in store.recent(100)]
        return {"rows": rows, "scope": "Most recent 100 assessments; currencies are not summed together",
                "totals": {"assessments": len(rows),
                           "high_risk": sum(r["risk_level"] in ("HIGH", "CRITICAL") for r in rows),
                           "completed": sum(r["payment_status"] == "COMPLETED" for r in rows),
                           "refunded": sum(r["payment_status"] == "REFUNDED" for r in rows)}}

    return router
