import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app import ingest
from app.agents import base, orchestrator
from app.config import Settings
from app.main import create_app


def make_settings(tmp_path, **kw) -> Settings:
    defaults = dict(
        paypal_client_id="cid", paypal_client_secret="secret", paypal_webhook_id="WH-1",
        public_base_url="https://trustpay.example", llm_provider="anthropic", llm_api_key="sk-test",
        db_path=str(tmp_path / "t.db"),
    )
    defaults.update(kw)
    return Settings(**defaults)


class FakePayPal:
    """Stateful stand-in for the PayPal REST API, served through httpx.MockTransport."""

    def __init__(self):
        self.orders: dict[str, dict[str, Any]] = {}
        self.requests: list[httpx.Request] = []
        self.capture_value_override: str | None = None
        self.webhook_valid = True
        self.captured: dict[str, dict[str, Any]] = {}  # order id -> captured order body
        self.verify_bodies: list[bytes] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.requests.append(req)
        p = req.url.path
        if p == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3600})
        if p == "/v2/checkout/orders" and req.method == "POST":
            body = json.loads(req.content)
            oid = f"ORDER{len(self.orders) + 1}"
            self.orders[oid] = body["purchase_units"][0]
            return httpx.Response(201, json={
                "id": oid, "status": "PAYER_ACTION_REQUIRED",
                "links": [{"rel": "payer-action", "href": f"https://www.sandbox.paypal.com/checkoutnow?token={oid}"}],
            })
        if p.endswith("/capture"):
            oid = p.split("/")[-2]
            if oid not in self.orders:
                return httpx.Response(404, json={"name": "RESOURCE_NOT_FOUND", "message": "order not found", "debug_id": "dbg-404"})
            if oid in self.captured:
                return httpx.Response(422, json={"name": "UNPROCESSABLE_ENTITY", "debug_id": "dbg-422",
                                                 "details": [{"issue": "ORDER_ALREADY_CAPTURED"}]})
            unit = self.orders[oid]
            amount = dict(unit["amount"])
            if self.capture_value_override:
                amount["value"] = self.capture_value_override
            body = {
                "id": oid, "status": "COMPLETED", "payer": {"email_address": "buyer@example.com"},
                "purchase_units": [{"payments": {"captures": [
                    {"id": f"CAP-{oid}", "status": "COMPLETED", "amount": amount, "custom_id": unit["custom_id"]}
                ]}}],
            }
            self.captured[oid] = body
            return httpx.Response(201, json=body)
        if p.startswith("/v2/checkout/orders/") and req.method == "GET":
            oid = p.split("/")[-1]
            if oid in self.captured:
                return httpx.Response(200, json=self.captured[oid])
            if oid in self.orders:
                return httpx.Response(200, json={"id": oid, "status": "APPROVED", "purchase_units": [self.orders[oid]]})
        if p.startswith("/v2/payments/captures/") and p.endswith("/refund"):
            return httpx.Response(201, json={"id": "REF1", "status": "COMPLETED"})
        if p == "/v1/notifications/verify-webhook-signature":
            self.verify_bodies.append(req.content)
            return httpx.Response(200, json={"verification_status": "SUCCESS" if self.webhook_valid else "FAILURE"})
        return httpx.Response(404, json={"name": "RESOURCE_NOT_FOUND", "message": "not found", "debug_id": "dbg"})


@pytest.fixture
def llm_down(monkeypatch):
    async def none(*_a, **_k):
        return None
    for mod in (base, orchestrator, ingest):
        monkeypatch.setattr(mod, "complete_json", none)


@pytest.fixture
def fake_paypal():
    return FakePayPal()


@pytest.fixture
def client(tmp_path, fake_paypal, llm_down):
    app = create_app(make_settings(tmp_path), paypal_transport=httpx.MockTransport(fake_paypal))
    return TestClient(app)
