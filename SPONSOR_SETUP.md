# TrustPay AI — sponsor integration setup

## Included in this update

- **Channel3:** authenticated, server-side product search at `POST /api/products/search`. Normalized product cards show offers, merchant links, currency and retrieval time. API keys never reach the browser. Missing credentials, exhausted quota and upstream failures produce explicit errors.
- **AG Studio by AG Grid:** React analytics dashboard connected to `GET /api/analytics`, with a purchase/payment table, risk chart, editable reports and live summary cards. It uses persisted application records rather than invented metrics.
- **Render:** a multi-stage Docker build serves the frontend and backend from one origin. The Blueprint includes a persistent SQLite disk.
- **Purchase UI:** URL/manual review, per-agent findings, questions for the seller, approval/rejection, PayPal sandbox redirect and payment/audit refresh.
- Fixed the existing `seller.paypal_email` URL override mismatch with the README.

## 1. Configure the backend

Python 3.11+ and Node 22+ are recommended.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in PayPal sandbox client ID/secret, your LLM provider/key and a currently available model ID. The original model default is retained for compatibility; set `LLM_MODEL` explicitly to a model your provider account supports.

Get a Channel3 key at https://trychannel3.com/developers and set `CHANNEL3_API_KEY` in `backend/.env`. The hackathon sponsor page advertises promo code `PAYPAL-HACKATHON-2026`; verify the offer when signing up. Do not put this key in any `VITE_` variable.

For local development set:

```dotenv
FRONTEND_URL=http://localhost:5173
```

Run the backend from the backend directory:

```bash
uvicorn app.main:create_app --factory --reload --port 8000
```

## 2. Run the frontend

In a second terminal:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to port 8000. If `TRUSTPAY_API_KEY` is configured, enter it in Connection settings and click Connect / refresh. It stays in memory, so re-enter it after reload/PayPal return. Do not embed a shared backend key in the frontend bundle.

AG Studio can be evaluated locally without a license, with trial warnings/watermarks. Obtain the sponsor trial license before a hosted demonstration:
https://www.ag-grid.com/studio/react/licence-install/

Set `VITE_AG_STUDIO_LICENSE_KEY` in `frontend/.env` and restart/rebuild. This is a frontend license value, not a service API secret. The MIT license covers this project's own source; AG Studio remains subject to its separate commercial/trial license.

## 3. Deploy on Render

1. Push this complete folder to your public repository.
2. Create a Render Blueprint using `render.yaml`.
3. Supply the requested PayPal, LLM, Channel3 and AG Studio values.
4. Set **both** `PUBLIC_BASE_URL` and `FRONTEND_URL` to your actual Render HTTPS service URL. Redeploy after setting them. Same-origin hosting needs no CORS setting.
5. Register `https://YOUR-SERVICE/api/paypal/webhook` in the PayPal sandbox app; use the event subscriptions in the main README.
6. Enter the generated `TRUSTPAY_API_KEY` through the UI connection panel.

The Blueprint uses a paid Starter service and a 1 GB persistent disk. Check Render's current pricing/credits before deploying. One service instance is intentional because storage uses SQLite. Render Workflows is **not** integrated or required by this build; agent orchestration remains inside FastAPI.

Docker builds use the lockfile. To build locally with the optional trial license:

```bash
docker build --build-arg VITE_AG_STUDIO_LICENSE_KEY="YOUR_TRIAL_LICENSE" -t trustpay-ai .
docker run -p 8000:8000 --env-file backend/.env -v trustpay-data:/data trustpay-ai
```

When serving the bundled UI locally on port 8000, set `FRONTEND_URL=http://localhost:8000`.

## 4. Demonstrate the full flow

1. Enter a listing URL or manual title/price/seller/description. Review the agent findings and AI status.
2. Search the exact product model with Channel3 and inspect the returned offers. Match currency, variant and condition manually; shipping/tax can differ. Results are comparison candidates, not verified safe sellers.
3. Approve or reject. High risk requires acknowledgement; critical risk also requires a note.
4. For a test purchase, use a merchant-controlled sandbox listing and complete PayPal with your sandbox buyer account.
5. Return to TrustPay, reconnect the access key if needed and refresh the payment/audit trail.
6. Open Analytics studio to explore the persisted assessment, risk score and payment status.

**Retailer comparison links are external links.** They do not execute PayPal checkout on the retailer's behalf. In the manual UI, checkout pays the sandbox app merchant. Do not represent it as a real retailer purchase, an escrow service or a guarantee of buyer protection.

## API additions

| Endpoint | Purpose |
| --- | --- |
| POST `/api/products/search` | Body: `{"query":"Sony WH-1000XM5 headphones", "limit":6, "currency":"USD"}` |
| GET `/api/analytics` | Last 100 persisted assessments and count-based summary metrics |
| GET `/api/sponsors/status` | Non-secret sponsor configuration status |

All three respect the existing optional `X-API-Key`. Search uses the existing per-IP analysis rate limiter. `currency` identifies the comparison context; it does not convert or filter provider prices. Returned offer currencies remain explicit. Search results do not automatically alter risk scores, set payment recipients or create orders.

## Verification and limits

Backend regression tests use mocked PayPal/Channel3 transports and stubbed LLM calls; these are test fixtures only. Live integrations require real keys and a real sandbox run before submission. There is no fake runtime product feed or fake payment success.

This is a single-operator hackathon prototype: the shared API key is not user authentication or per-user authorization. Do not expose private customer records or distribute a merchant admin key to public visitors. Refund actions remain backend-only. The dashboard uses the most recent 100 assessments, and does not add amounts across different currencies.

AG Studio includes preconfigured table/chart widgets and editable reports. A custom Studio agent harness and custom Studio widget extensions are not included. Sponsor award eligibility depends on the organizer's criteria; merely listing a sponsor is not a claim of eligibility.

## Official references

- Channel3 sponsor: https://paypalaihackathon.devpost.com/details/channel3
- Channel3 search request: https://www.trychannel3.com/product-data/arts-entertainment-hobbies-creative-arts-arts-crafts-art-crafting-tools-color-mixing-tools-palettes
- Channel3 offer fields: https://connect.trychannel3.com/blog/build-ai-shopping-app-no-code
- AG Studio React: https://www.ag-grid.com/studio/react/quick-start/
- AG Studio license: https://www.ag-grid.com/studio/react/licence-install/
- Render sponsor: https://paypalaihackathon.devpost.com/details/render

Validation: **57 backend tests**, **3 frontend aggregation checks**, and the Vite production build passed. Browser checks use stubbed API responses to verify navigation, purchase review/approval, selected checkout language submission, comparisons, developer diagnostics, AG Studio editing and mobile layouts. Live PayPal-hosted language behavior and Render deployment still require your account credentials.

## PayPal checkout languages

English (default), Arabic and French are available in the **PayPal checkout language** dropdown above the payment button. This selects the PayPal-hosted checkout language; the TrustPay interface and AI reports remain English. The API accepts `{"locale":"en-US"}`, `{"locale":"ar-AE"}` or `{"locale":"fr-FR"}` on POST `/api/assessments/{id}/orders`. Omitting the body uses `PAYPAL_LOCALE` (default `en-US`). The chosen locale is stored with the assessment. Reusing an open order preserves its original locale and never creates a duplicate payment to change language. Requests explicitly choosing a different locale now return 409 with instructions to start a fresh assessment. Older orders without a stored locale also keep their existing checkout experience. Select the language on a fresh assessment before creating the order. PayPal ultimately controls the hosted page and may apply regional/account fallbacks.

### Update an existing local installation

Stop both servers. Back up your current folder. Copy the new `backend/app`, `frontend/src`, and documentation into your existing project; preserve `backend/.env`, `frontend/.env`, and your database. Restart the backend using `.venv/bin/python -m uvicorn app.main:create_app --factory --reload --port 8000` and the frontend with `npm run dev`. Optional: add `PAYPAL_LOCALE=en-US` to backend/.env. If extracting to a new folder instead, copy your environment files and database into it and install dependencies as above.

LLM failures now log only exception types, so malformed authentication headers cannot print keys in application warning messages. Rotate any key that was already exposed in previous logs.

## Professional workspace refresh

See [UPDATE_LOCAL.md](UPDATE_LOCAL.md). The Developer page reads `/api/developer/status` behind the same access key. Metrics, charts, payment history and integration cards are wired to stored data and current configuration. Configuration cards do not claim that a provider has been tested live.
