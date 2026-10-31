"""Payee routing, currencies, order reuse, redirects, webhook capture/refund paths, rate limits."""
import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from app.agents import base
from app.agents.specialists import PriceAgent
from app.config import Settings, format_amount
from app.main import create_app

from .conftest import make_settings
from .fixtures import CLEAN
from .test_flow import WEBHOOK_HEADERS, analyze, approve_and_order


def make_client(tmp_path, fake_paypal, **kw):
    return TestClient(create_app(make_settings(tmp_path, **kw), paypal_transport=httpx.MockTransport(fake_paypal)))


def sent_orders(fake_paypal):
    return [json.loads(r.content) for r in fake_paypal.requests if r.url.path == "/v2/checkout/orders"]


def test_public_config(client):
    body = client.get("/api/config").json()
    assert body == {"paypal_client_id": "cid", "paypal_env": "sandbox", "currency": "USD", "api_key_required": False}
    assert "secret" not in json.dumps(body)


def test_order_pays_seller_when_paypal_email_given(client, fake_paypal):
    listing = CLEAN.model_copy(deep=True)
    listing.seller.paypal_email = "seller@business.example.com"
    order = approve_and_order(client, analyze(client, listing))
    assert order["payee"] == "seller@business.example.com"
    assert sent_orders(fake_paypal)[0]["purchase_units"][0]["payee"] == {"email_address": "seller@business.example.com"}


def test_order_without_seller_email_pays_app_account(client, fake_paypal):
    approve_and_order(client, analyze(client, CLEAN))
    assert "payee" not in sent_orders(fake_paypal)[0]["purchase_units"][0]


def test_invalid_seller_email_rejected(client):
    data = CLEAN.model_dump()
    data["seller"]["paypal_email"] = "not-an-email"
    assert client.post("/api/analyze", json=data).status_code == 422


def test_zero_decimal_currency_and_capture_verification(client, fake_paypal):
    assert format_amount(1999.0, "JPY") == "1999" and format_amount(19.5, "usd") == "19.50"
    listing = CLEAN.model_copy(deep=True)
    listing.currency, listing.price, listing.market_price = "JPY", 25000, 27000
    a = analyze(client, listing)
    order = approve_and_order(client, a)
    assert sent_orders(fake_paypal)[0]["purchase_units"][0]["amount"] == {"currency_code": "JPY", "value": "25000"}
    cap = client.get(f"/api/paypal/return?token={order['order_id']}").json()
    assert cap["verified"] is True


def test_unsupported_currency_blocked_at_order(client):
    listing = CLEAN.model_copy(deep=True)
    listing.currency = "AED"
    a = analyze(client, listing)  # analysis still works
    client.post(f"/api/assessments/{a['id']}/decision", json={"approve": True})
    r = client.post(f"/api/assessments/{a['id']}/orders")
    assert r.status_code == 422 and "AED" in r.json()["detail"]


def test_open_order_is_reused_and_retry_gets_new_key(client, fake_paypal):
    a = analyze(client, CLEAN)
    first = approve_and_order(client, a)
    again = client.post(f"/api/assessments/{a['id']}/orders").json()
    assert again["reused"] and again["order_id"] == first["order_id"]
    assert len(sent_orders(fake_paypal)) == 1

    # Simulate a denied capture, then a retry: new order with a new idempotency key.
    from app.db import Store
    store: Store = client.app.state.store
    stored = store.get(a["id"])
    stored.payment_status = "DENIED"
    store.save(stored)
    retry = client.post(f"/api/assessments/{a['id']}/orders").json()
    assert not retry["reused"] and retry["order_id"] != first["order_id"]
    keys = [r.headers["PayPal-Request-Id"] for r in fake_paypal.requests if r.url.path == "/v2/checkout/orders"]
    assert keys == [f"order-{a['id']}-1", f"order-{a['id']}-2"]


def test_return_and_cancel_redirect_to_frontend(tmp_path, fake_paypal, llm_down):
    c = make_client(tmp_path, fake_paypal, frontend_url="https://app.trustpay.example")
    a = analyze(c, CLEAN)
    order = approve_and_order(c, a)
    r = c.get(f"/api/paypal/return?token={order['order_id']}", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("https://app.trustpay.example/?assessment_id=" + a["id"])
    assert "status=COMPLETED" in r.headers["location"] and "verified=True" in r.headers["location"]
    r = c.get(f"/api/paypal/cancel?token={order['order_id']}", follow_redirects=False)
    assert r.status_code == 303 and "CANCELLED_BY_BUYER" in r.headers["location"]


def test_webhook_sends_raw_event_bytes_for_verification(client, fake_paypal):
    raw = '{"id":"WH-RAW","event_type":"PAYMENT.CAPTURE.COMPLETED","resource":{"amount":{"value":"10.50"}}}'
    client.post("/api/paypal/webhook", content=raw, headers={**WEBHOOK_HEADERS, "Content-Type": "application/json"})
    body = fake_paypal.verify_bodies[-1].decode()
    assert body.endswith('"webhook_event": ' + raw + "}")
    assert json.loads(body)["webhook_id"] == "WH-1"


def test_webhook_order_approved_captures_when_buyer_never_returned(client, fake_paypal):
    a = analyze(client, CLEAN)
    order = approve_and_order(client, a)
    event = {"id": "WH-A1", "event_type": "CHECKOUT.ORDER.APPROVED",
             "resource": {"id": order["order_id"], "purchase_units": [{"custom_id": f"trustpay:{a['id']}:LOW"}]}}
    r = client.post("/api/paypal/webhook", json=event, headers=WEBHOOK_HEADERS).json()
    assert r == {"status": "captured", "verified": True}
    assert client.get(f"/api/assessments/{a['id']}").json()["payment_status"] == "COMPLETED"
    # The buyer's browser arrives late: no double capture, no error.
    assert client.get(f"/api/paypal/return?token={order['order_id']}").json()["already_captured"]


def test_already_captured_race_is_recovered(client, fake_paypal):
    a = analyze(client, CLEAN)
    order = approve_and_order(client, a)
    client.post(f"/api/assessments/{a['id']}/capture")
    # Pretend our DB missed the first capture result; PayPal now says ORDER_ALREADY_CAPTURED.
    store = client.app.state.store
    stored = store.get(a["id"])
    stored.payment_status = "APPROVED"
    store.save(stored)
    cap = client.post(f"/api/assessments/{a['id']}/capture").json()
    assert cap["verified"] and cap["capture_id"] == f"CAP-{order['order_id']}"


def test_refund_webhook_found_via_capture_link(client, fake_paypal):
    a = analyze(client, CLEAN)
    order = approve_and_order(client, a)
    client.get(f"/api/paypal/return?token={order['order_id']}")
    cap_id = f"CAP-{order['order_id']}"
    event = {"id": "WH-R1", "event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {
        "id": "REF-9", "links": [{"rel": "up", "href": f"https://api.sandbox.paypal.com/v2/payments/captures/{cap_id}"}]}}
    assert client.post("/api/paypal/webhook", json=event, headers=WEBHOOK_HEADERS).json()["status"] == "processed"
    stored = client.get(f"/api/assessments/{a['id']}").json()
    assert stored["payment_status"] == "REFUNDED" and stored["capture_id"] == cap_id


def test_late_pending_webhook_does_not_downgrade(client, fake_paypal):
    a = analyze(client, CLEAN)
    order = approve_and_order(client, a)
    client.get(f"/api/paypal/return?token={order['order_id']}")
    event = {"id": "WH-P1", "event_type": "PAYMENT.CAPTURE.PENDING", "resource": {"id": "X", "custom_id": f"trustpay:{a['id']}:LOW"}}
    client.post("/api/paypal/webhook", json=event, headers=WEBHOOK_HEADERS)
    assert client.get(f"/api/assessments/{a['id']}").json()["payment_status"] == "COMPLETED"


def test_rate_limit(tmp_path, fake_paypal, llm_down):
    c = make_client(tmp_path, fake_paypal, rate_limit_per_min=2)
    assert c.post("/api/analyze", json=CLEAN.model_dump()).status_code == 200
    assert c.post("/api/analyze", json=CLEAN.model_dump()).status_code == 200
    r = c.post("/api/analyze", json=CLEAN.model_dump())
    assert r.status_code == 429 and r.headers["retry-after"] == "60"


SETTINGS = Settings(paypal_client_id="x", paypal_client_secret="y", llm_api_key="z")


def run_price(monkeypatch, listing, estimate, confidence):
    async def fake_llm(_s, system, _u, **_k):
        assert "estimated_market_price" in system
        return {"additional_findings": [], "score_adjustment": 0, "summary": "s",
                "estimated_market_price": estimate, "estimate_confidence": confidence}
    monkeypatch.setattr(base, "complete_json", fake_llm)
    return asyncio.run(PriceAgent().run(listing, SETTINGS))


def test_ai_price_estimate_used_only_without_buyer_price(monkeypatch):
    listing = CLEAN.model_copy(deep=True)
    listing.market_price, listing.price = None, 100

    report = run_price(monkeypatch, listing, 500, "high")
    ai = [f for f in report.findings if f.signal == "[AI] Far below estimated market price"]
    assert ai and ai[0].severity.value == "HIGH" and ai[0].points <= base.LLM_MAX_EXTRA_POINTS
    assert "80% below" in ai[0].detail

    assert not [f for f in run_price(monkeypatch, listing, 500, "low").findings if f.signal.startswith("[AI] Far")]
    assert not [f for f in run_price(monkeypatch, listing, "abc", "high").findings if f.signal.startswith("[AI] Far")]

    listing.market_price = 120  # buyer-supplied price wins; estimate ignored
    assert not [f for f in run_price(monkeypatch, listing, 500, "high").findings if f.signal.startswith("[AI] Far")]


def test_malformed_llm_findings_are_ignored(monkeypatch):
    async def fake_llm(*_a, **_k):
        return {"additional_findings": ["oops", {"signal": "ok", "severity": "LOW"}], "score_adjustment": "x"}
    monkeypatch.setattr(base, "complete_json", fake_llm)
    report = asyncio.run(PriceAgent().run(CLEAN, SETTINGS))
    assert [f.signal for f in report.findings if f.signal.startswith("[AI]")] == ["[AI] ok"]
