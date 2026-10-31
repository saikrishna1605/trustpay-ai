"""PayPal REST client: OAuth, Orders v2, Payments v2 refunds, webhook verification."""
from __future__ import annotations

import json as jsonlib
import time
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Any, Optional

import httpx

from .config import Settings, format_amount


def localized_approval_url(url: Optional[str], locale: str) -> Optional[str]:
    """Preserve PayPal's order token and add a hosted-page language hint.

    experience_context.locale is authoritative at order creation. The extra
    locale.x hint also requests the desired language when following the link;
    PayPal may still apply logged-in account or regional preferences.
    """
    if not url:
        return url
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "locale.x"]
    query.append(("locale.x", {"en-US": "en_US", "ar-AE": "ar_AE", "fr-FR": "fr_FR"}[locale]))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class PayPalError(RuntimeError):
    def __init__(self, message: str, status: int = 502, debug_id: Optional[str] = None, details: Any = None):
        super().__init__(message)
        self.status = status
        self.debug_id = debug_id
        self.details = details


class PayPalClient:
    def __init__(self, settings: Settings, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.s = settings
        self._transport = transport  # injectable for tests
        self._token: Optional[str] = None
        self._token_exp = 0.0

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.s.paypal_base_url, timeout=30, transport=self._transport)

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        resp = await client.post(
            "/v1/oauth2/token",
            auth=(self.s.paypal_client_id, self.s.paypal_client_secret),
            data={"grant_type": "client_credentials"},
        )
        if resp.status_code != 200:
            raise PayPalError(f"PayPal authentication failed ({resp.status_code}). Check client id/secret.", resp.status_code)
        body = resp.json()
        self._token = body["access_token"]
        self._token_exp = time.time() + int(body.get("expires_in", 300))
        return self._token

    async def request(
        self, method: str, path: str, json: Optional[dict] = None, idempotency_key: Optional[str] = None, raw_body: Optional[str] = None
    ) -> dict[str, Any]:
        async with self._client() as client:
            token = await self._access_token(client)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }
            if method != "GET":
                headers["PayPal-Request-Id"] = idempotency_key or uuid.uuid4().hex
            if raw_body is not None:
                resp = await client.request(method, path, content=raw_body.encode(), headers=headers)
            else:
                resp = await client.request(method, path, json=json, headers=headers)
        if resp.status_code >= 400:
            try:
                body = resp.json()
            except ValueError:
                body = {}
            raise PayPalError(
                body.get("message") or body.get("name") or f"PayPal error {resp.status_code}",
                resp.status_code,
                body.get("debug_id"),
                body.get("details"),
            )
        return resp.json() if resp.content else {}

    async def verify_credentials(self) -> None:
        async with self._client() as client:
            await self._access_token(client)

    # ---- Orders v2 -------------------------------------------------------
    async def create_order(
        self, *, amount: float, currency: str, description: str, assessment_id: str, risk_level: str,
        payee_email: Optional[str] = None, attempt: int = 1, locale: Optional[str] = None,
    ) -> dict[str, Any]:
        unit: dict[str, Any] = {
            "reference_id": assessment_id,
            "custom_id": f"trustpay:{assessment_id}:{risk_level}",
            "invoice_id": f"trustpay-{assessment_id}-{attempt}",
            "description": description[:127],
            "amount": {"currency_code": currency, "value": format_amount(amount, currency)},
        }
        if payee_email:
            # Pay the seller's own PayPal account instead of the app owner's.
            unit["payee"] = {"email_address": payee_email}
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [unit],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "brand_name": "TrustPay AI",
                        "locale": locale or self.s.paypal_locale,
                        "user_action": "PAY_NOW",
                        "shipping_preference": "NO_SHIPPING",
                        "return_url": f"{self.s.public_base_url}/api/paypal/return",
                        "cancel_url": f"{self.s.public_base_url}/api/paypal/cancel",
                    }
                }
            },
        }
        # Same assessment + attempt -> same idempotency key, so network retries don't create duplicate orders.
        order = await self.request("POST", "/v2/checkout/orders", payload, idempotency_key=f"order-{assessment_id}-{attempt}")
        approve = next(
            (link["href"] for link in order.get("links", []) if link.get("rel") in ("payer-action", "approve")),
            None,
        )
        return {"id": order["id"], "status": order["status"], "approve_url": localized_approval_url(approve, locale or self.s.paypal_locale)}

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/v2/checkout/orders/{order_id}")

    async def capture_order(self, order_id: str) -> dict[str, Any]:
        try:
            order = await self.request("POST", f"/v2/checkout/orders/{order_id}/capture", idempotency_key=f"capture-{order_id}")
        except PayPalError as exc:
            # The webhook (or another tab) captured it first: read the order and report that capture.
            if not _has_issue(exc, "ORDER_ALREADY_CAPTURED"):
                raise
            order = await self.get_order(order_id)
        return self.parse_capture(order)

    @staticmethod
    def parse_capture(order: dict[str, Any]) -> dict[str, Any]:
        unit = (order.get("purchase_units") or [{}])[0]
        capture = ((unit.get("payments") or {}).get("captures") or [{}])[0]
        return {
            "order_id": order.get("id"),
            "order_status": order.get("status"),
            "capture_id": capture.get("id"),
            "capture_status": capture.get("status"),
            "amount": capture.get("amount"),
            "custom_id": capture.get("custom_id") or unit.get("custom_id"),
            "payer_email": (order.get("payer") or {}).get("email_address"),
        }

    # ---- Payments v2 -----------------------------------------------------
    async def refund_capture(self, capture_id: str, note: str) -> dict[str, Any]:
        refund = await self.request(
            "POST", f"/v2/payments/captures/{capture_id}/refund", {"note_to_payer": note[:255]}, idempotency_key=f"refund-{capture_id}"
        )
        return {"refund_id": refund.get("id"), "status": refund.get("status"), "amount": refund.get("amount")}

    # ---- Webhooks --------------------------------------------------------
    async def verify_webhook(self, headers: dict[str, str], raw_event: str) -> bool:
        """Verify with PayPal's postback API.

        The event is spliced in as the exact bytes PayPal sent: re-serializing parsed JSON can change
        number formatting or key order and make a genuine event fail verification.
        """
        if not self.s.paypal_webhook_id:
            raise PayPalError("PAYPAL_WEBHOOK_ID is not configured", 500)
        h = {k.lower(): v for k, v in headers.items()}
        body = {
            "auth_algo": h.get("paypal-auth-algo"),
            "cert_url": h.get("paypal-cert-url"),
            "transmission_id": h.get("paypal-transmission-id"),
            "transmission_sig": h.get("paypal-transmission-sig"),
            "transmission_time": h.get("paypal-transmission-time"),
            "webhook_id": self.s.paypal_webhook_id,
        }
        if not all(body[k] for k in ("auth_algo", "cert_url", "transmission_id", "transmission_sig", "transmission_time")):
            return False
        raw = jsonlib.dumps(body)[:-1] + ', "webhook_event": ' + raw_event + "}"
        result = await self.request("POST", "/v1/notifications/verify-webhook-signature", raw_body=raw)
        return result.get("verification_status") == "SUCCESS"


def _has_issue(exc: PayPalError, issue: str) -> bool:
    details = exc.details if isinstance(exc.details, list) else []
    return any(isinstance(d, dict) and d.get("issue") == issue for d in details)
