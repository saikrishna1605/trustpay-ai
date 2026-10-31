"""URL ingestion: structured data, LLM extraction, SSRF guard, API overrides."""
import asyncio
import json

import httpx
import pytest

from app import ingest

from .conftest import make_settings

PAGE = """<html><head><title>Console deal</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"Gaming console 1TB",
"description":"Sealed console","offers":{"@type":"Offer","price":"149.00","priceCurrency":"USD",
"seller":{"@type":"Organization","name":"deals4u"}}}</script></head>
<body><h1>Gaming console 1TB</h1><p>All sales final. Ships in 30 days. Pay via friends and family for discount.</p>
<p>Seller joined 6 days ago.</p></body></html>"""


def site(req: httpx.Request) -> httpx.Response:
    if req.url.path == "/old":
        return httpx.Response(302, headers={"location": "/listing"})
    if req.url.path == "/listing":
        return httpx.Response(200, html=PAGE)
    return httpx.Response(404)


def test_json_ld_parsing():
    from bs4 import BeautifulSoup
    ld = ingest.parse_json_ld(BeautifulSoup(PAGE, "html.parser"))
    assert ld == {"title": "Gaming console 1TB", "description": "Sealed console", "price": "149.00", "currency": "USD", "seller_name": "deals4u"}


def test_listing_from_url_merges_structured_data_and_llm(tmp_path, monkeypatch):
    seen = {}

    async def fake_llm(_s, system, user, **_k):
        seen["user"] = user
        return {"title": "WRONG", "price": 999, "seller_account_age_days": 6, "return_policy": "All sales final",
                "shipping_days": 30, "suspicious_text": ["Pay via friends and family for discount"]}

    monkeypatch.setattr(ingest, "complete_json", fake_llm)
    listing, missing = asyncio.run(ingest.listing_from_url(
        "https://shop.example/old", make_settings(tmp_path), transport=httpx.MockTransport(site), check_host=False))
    assert listing.title == "Gaming console 1TB" and listing.price == 149.0  # structured data wins
    assert listing.url == "https://shop.example/listing"  # redirect followed
    assert listing.seller.name == "deals4u" and listing.seller.account_age_days == 6
    assert "friends and family" in listing.description
    assert "seller.rating" in missing and "market_price" in missing
    assert "<page_text>" in seen["user"]


@pytest.mark.parametrize("url", ["http://127.0.0.1/x", "http://localhost:8000/", "http://169.254.169.254/latest", "file:///etc/passwd"])
def test_ssrf_guard(url):
    with pytest.raises(ingest.IngestError):
        asyncio.run(ingest._assert_public_host(url))


def test_analyze_url_endpoint(client, monkeypatch):
    async def fake_listing(url, settings, **_k):
        from .fixtures import SCAM
        l = SCAM.model_copy(deep=True)
        l.market_price, l.seller_messages, l.url = None, [], url
        return l, ["market_price", "seller.rating"]

    monkeypatch.setattr("app.main.listing_from_url", fake_listing)
    r = client.post("/api/analyze/url", json={
        "url": "https://shop.example/listing", "market_price": 499,
        "seller_messages": ["send as friends and family"], "overrides": {"seller.rating": 2.0},
    })
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["source"] == "url" and a["missing_fields"] == []
    assert a["listing"]["market_price"] == 499 and a["listing"]["seller"]["rating"] == 2.0
    assert client.post("/api/analyze/url", json={"url": "https://x.example", "overrides": {"price": 1, "evil": 1}}).status_code == 422
