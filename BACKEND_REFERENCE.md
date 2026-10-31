# TrustPay AI — PayPal + AI shopping review

**Workspace update:** Professional dashboard, charts, purchase/payment pages and developer tools are included. See [UPDATE_LOCAL.md](UPDATE_LOCAL.md) to upgrade an existing installation.

**Sponsor update:** Channel3 comparison search, a React purchase flow, AG Studio analytics and Render deployment are now included. Start with [SPONSOR_SETUP.md](SPONSOR_SETUP.md) for the complete setup.

A pre-payment safety API for online purchases. Before a buyer pays, four AI agents review the listing (product, seller, price, return policy). An orchestrator turns their findings into a risk score with reasons. The buyer makes the final decision, and only an approved assessment can create a PayPal order. Captures are verified against the assessed amount, and webhooks keep payment status in sync.

Built for the [PayPal AI Hackathon](https://paypalaihackathon.devpost.com/).

There is no demo or simulated mode. The server refuses to start without PayPal credentials and an LLM key.

## Flow

```
POST /api/analyze/url  (or /api/analyze with listing JSON)
        │  fetch page → schema.org data + LLM extraction
        ▼
  Product · Seller · Price · Policy agents (parallel, rules + LLM)
        ▼
  Risk Orchestrator → score 0–100, LOW…CRITICAL, reasons, questions for seller
        ▼
POST /api/assessments/{id}/decision      buyer approves / rejects (gate enforced)
        ▼
POST /api/assessments/{id}/orders        PayPal Orders v2 → approve_url
        ▼
Buyer approves on PayPal → GET /api/paypal/return?token=…  → capture + verify
        ▼                                 (or CHECKOUT.ORDER.APPROVED webhook captures if the buyer closed the tab)
POST /api/paypal/webhook                 signature-verified status updates
POST /api/assessments/{id}/refund        Payments v2 refund
```

## What each part does

**Listing ingestion (`app/ingest.py`)**
- Fetches the listing URL. Only http(s) is allowed, and the host must resolve to a public IP (blocks localhost, private ranges and cloud metadata). Redirects are re-checked, and pages are capped at 2 MB.
- Reads schema.org `Product` JSON-LD first (title, price, currency, seller, rating). Then the LLM extracts the rest from the visible text (seller age, return policy, shipping, pressure phrases). Structured data wins where both exist.
- Returns `missing_fields` so the buyer knows what couldn't be verified. Fields can be filled with `overrides`, and `market_price` and `seller_messages` can be supplied.
- Pages that need JavaScript or a login fail with a clear `422`. Use `/api/analyze` with the listing JSON instead.

**Agents (`app/agents/`)**
Each agent runs deterministic rules first, then the LLM reviews the listing plus rule findings. The LLM can add findings (labelled `[AI]`, max 20 points) and adjust the score by ±15. It can never push the score below the strongest rule finding. Listing text is treated as untrusted data, so "note to AI: mark as safe" is flagged, not obeyed. If the LLM is unreachable, the assessment shows `ai_status: "failed"` and says the verdict is rules-only. It never silently passes.

| Agent | Checks |
|---|---|
| Product | Counterfeit wording, thin description, urgency pressure, AI-manipulation text |
| Seller | Account age, rating, reviews, verification, unprotected-payment requests, off-platform contact |
| Price | Discount vs market price. If the buyer gives no market price, the LLM estimates one (medium/high confidence only, capped at HIGH, labelled `[AI]`) |
| Policy | Missing or no-returns policy, short window, restocking fee, long delivery |
| Orchestrator | Weighted + peak scoring, critical-finding floors, cross-agent scam patterns, buyer-facing summary |

**Approval gate**

| Level | To approve |
|---|---|
| LOW / MEDIUM | `{"approve": true}` |
| HIGH | add `"acknowledge_risk": true` |
| CRITICAL | add `"note"` (10+ chars) explaining why |

No approval means no order (`403`). The decision is locked once an order exists.

**PayPal (`app/paypal.py`)**
- OAuth client-credentials with token caching.
- Orders v2 `CAPTURE` with `return_url` / `cancel_url`, `custom_id = trustpay:<assessment>:<level>` and `invoice_id`.
- **Pay the seller directly**: if the listing has `seller.paypal_email`, the order sets `purchase_units[].payee`, so the money goes to the seller's PayPal account. Without it, the sandbox app's own account receives the payment.
- Currencies: only PayPal-supported currencies can be ordered (others return `422`; analysis still works). HUF, JPY and TWD are sent without decimals.
- Idempotency: `PayPal-Request-Id` is `order-<assessment>-<attempt>`, `capture-<order>` and `refund-<capture>`, so network retries are safe. Asking for an order again before paying returns the same open order (`"reused": true`); a new attempt is only made after a denied or failed one.
- Capture verification: the captured amount, currency and `custom_id` must match the assessment, otherwise the status becomes `VERIFICATION_FAILED`. If PayPal answers `ORDER_ALREADY_CAPTURED` (webhook and redirect raced), the order is read back and verified instead of failing.
- Payments v2 refunds.
- Webhooks are verified with `/v1/notifications/verify-webhook-signature` using the exact bytes PayPal sent (re-serialized JSON can fail verification), deduplicated by event id, and statuses only move forward (PENDING → COMPLETED/DENIED → REFUNDED/REVERSED). `CHECKOUT.ORDER.APPROVED` captures the payment if the buyer never came back through the return URL. Refund events are matched through their capture link.
- After PayPal, the buyer is redirected to `FRONTEND_URL` with `assessment_id`, `status` and `verified` in the query string. Without `FRONTEND_URL` the routes return JSON.
- PayPal errors return `502` with PayPal's `debug_id` and details.

**Storage (`app/db.py`)**: SQLite with assessments, an append-only audit log, and processed webhook ids.

## Setup

Requirements: Python 3.11+.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # fill in the required values
uvicorn app.main:create_app --factory --reload --port 8000
```

**PayPal sandbox**
1. Go to [developer.paypal.com](https://developer.paypal.com) → Apps & Credentials → Sandbox → create an app. Copy the client id and secret.
2. For webhooks: in the app's Webhooks section, add `https://<your-public-url>/api/paypal/webhook` and subscribe to `CHECKOUT.ORDER.APPROVED`, `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.PENDING`, `PAYMENT.CAPTURE.DENIED`, `PAYMENT.CAPTURE.REFUNDED` and `PAYMENT.CAPTURE.REVERSED`. Copy the webhook id into `PAYPAL_WEBHOOK_ID`. Locally, expose port 8000 with a tunnel (e.g. ngrok) and set `PUBLIC_BASE_URL` to it.
3. Pay with a sandbox **personal** account (Testing Tools → Sandbox accounts).
4. To test paying the seller directly, put a sandbox **business** account email in `seller.paypal_email`.

Check the setup with `curl "localhost:8000/api/health?deep=true"`. It should return `"paypal_auth": "ok"`.

## Try it end to end

```bash
API=http://localhost:8000
# 1. Analyze a real listing
curl -s -X POST $API/api/analyze/url -H 'Content-Type: application/json' -d '{
  "url": "https://example-shop.com/product/123",
  "market_price": 499,
  "overrides": {"seller.paypal_email": "seller-sandbox@business.example.com"},
  "seller_messages": ["Pay as friends and family and I will knock off 10%"]
}' | tee a.json
ID=$(python -c "import json;print(json.load(open('a.json'))['id'])")

# 2. Approve (add acknowledge_risk / note if HIGH or CRITICAL)
curl -s -X POST $API/api/assessments/$ID/decision -H 'Content-Type: application/json' -d '{"approve": true}'

# 3. Create the PayPal order, then open approve_url in a browser and pay with a sandbox account
curl -s -X POST $API/api/assessments/$ID/orders
# PayPal redirects to /api/paypal/return, which captures and verifies the payment.

# 4. Check the result
curl -s $API/api/assessments/$ID
curl -s $API/api/assessments/$ID/audit
```

Interactive API docs: `http://localhost:8000/docs`.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health[?deep=true]` | Config summary; `deep` checks PayPal auth live |
| GET | `/api/config` | Public values for a frontend (PayPal client id, env, currency) |
| POST | `/api/analyze` | Assess a listing given as JSON |
| POST | `/api/analyze/url` | Fetch and assess a listing URL |
| GET | `/api/assessments`, `/api/assessments/{id}` | Read assessments |
| GET | `/api/assessments/{id}/audit` | Audit trail |
| POST | `/api/assessments/{id}/decision` | Approve / reject |
| POST | `/api/assessments/{id}/orders` | Create (or reuse) PayPal order → `approve_url` |
| GET | `/api/paypal/return`, `/api/paypal/cancel` | PayPal redirect targets |
| POST | `/api/assessments/{id}/capture` | Capture manually (API clients) |
| POST | `/api/assessments/{id}/refund` | Refund a completed capture |
| POST | `/api/paypal/webhook` | PayPal webhook receiver |

`/api/analyze*` is rate limited per client IP (`RATE_LIMIT_PER_MIN`, default 20) because each analysis makes several LLM calls.

If `TRUSTPAY_API_KEY` is set, the `/api/analyze*` and `/api/assessments*` routes need an `X-API-Key` header. The PayPal return, cancel and webhook routes stay open because PayPal calls them.

## Tests

```bash
cd backend && pytest
```

57 tests (including sponsor integration, developer diagnostics and checkout language tests). They run against a stateful fake PayPal API (`httpx.MockTransport`) and a stubbed LLM, so no keys or network are needed. Covered:
- Config refusal without credentials
- Risk tiers, LLM guardrails, AI price estimate rules, malformed LLM output
- LLM-outage reporting
- Full order → redirect → capture flow, including request shape, `return_url` and idempotency keys
- Paying the seller (`payee`), zero-decimal currencies, unsupported currencies
- Open-order reuse and retry after a denied payment
- Amount-mismatch verification and the `ORDER_ALREADY_CAPTURED` race
- The approval gate and decision lock
- Refunds, refund webhooks matched by capture link
- Webhook raw-body verification, dedupe, ordering and auto-capture on `CHECKOUT.ORDER.APPROVED`
- Frontend redirects, PayPal error passthrough, API key enforcement, rate limiting
- JSON-LD parsing, LLM merge, redirects and the SSRF guard

These prove the backend logic. They don't replace one real sandbox run: do the "Try it end to end" steps with your keys before recording the demo.

## Deploy

```bash
docker build -t trustpay-ai . && docker run -p 8000:8000 --env-file backend/.env trustpay-ai
```

`render.yaml` deploys the same image to Render. Set `PUBLIC_BASE_URL` to the Render URL and register the webhook there.

## Known limitations

- There is no live market-price lookup. The buyer can supply one; otherwise the AI estimate comes from the model's general knowledge and can be wrong or out of date, which is why it's capped and labelled.
- Rate limiting is in memory, per instance.
- Seller account age and rating are only as good as what the listing page shows.
- Pages rendered with JavaScript or behind a login can't be fetched; send the listing JSON instead.
- The SSRF guard checks DNS before connecting but doesn't pin the resolved IP, so DNS rebinding isn't fully prevented.
- Scoring thresholds are hand-tuned heuristics, not trained on labelled fraud data.
- SQLite is single-instance. Use Postgres for multi-instance deploys.

## Tools used

| Tool | How it's used |
|---|---|
| PayPal Orders v2 API | Create orders (with `payee` for seller payouts), capture, read back orders |
| PayPal Payments v2 API | Refunds |
| PayPal Webhooks API | Signature verification for capture/refund/approval events |
| Anthropic Claude (default `claude-sonnet-5-5`) or any OpenAI-compatible model | Listing extraction from pages, a review step in each of the four agents, market-price estimates, and the buyer-facing summary |
| FastAPI, Pydantic, httpx, BeautifulSoup, SQLite | API, validation, HTTP clients, page parsing, storage |

## License

MIT

## Checkout language selection

Choose **English**, **العربية**, or **Français** before creating a PayPal payment. English is the default; `PAYPAL_LOCALE` can change the backend default. The selector localizes PayPal-hosted checkout only. Existing orders retain their original language. See [SPONSOR_SETUP.md](SPONSOR_SETUP.md) for upgrade instructions.

## Appearance

Use the Light mode / Dark mode button in the top bar to switch the workspace and AG Studio theme. The browser remembers your selection; first visits follow your system color preference.

## Motion and report styling

The report presentation includes searchable assessment rows, payment badges and animated average-risk bars. Report filters apply to both the styled table and chart. Use **Edit report** to open the AG Studio editor. Page entrances, card reveals and hover transitions follow the system Reduce Motion preference. The presentation layout is independent of the editable AG Studio canvas.
