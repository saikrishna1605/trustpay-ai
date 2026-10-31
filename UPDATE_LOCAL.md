# Update your running TrustPay project

## Animated styling update

The Analytics Studio **View report** now uses a styled presentation with a searchable purchase table, individual assessment rows, payment badges and animated average-risk bars. Its filters apply to both the table and average-risk chart. **Edit report** still opens the genuine AG Studio editor with the same stored assessment data. Editor customization remains available while the presentation view has a fixed designed layout.

Short page entrances, card/row reveals, chart reveals, hover feedback and button transitions are applied across the workspace. The interface honors the operating system's Reduce Motion preference. No repeating animations are added to financial charts.

To apply this update, stop the frontend, copy `frontend/src` from this ZIP into your existing frontend and run `npm run dev`. If you have not applied the theme update yet, also copy `frontend/index.html`, `frontend/package.json` and `frontend/package-lock.json`, then run `npm ci`. Preserve all `.env` files, your backend and database.

## Light / dark theme update

Use the **Dark mode / Light mode** button in the top bar. It applies to all workspace pages and AG Studio, remembers your choice in this browser and follows the system preference on the first visit.

For this theme update, stop the frontend and copy only `frontend/src`, `frontend/index.html`, `frontend/package.json` and `frontend/package-lock.json` from this ZIP into your existing frontend. Preserve your `.env` files and database. From the frontend folder run `npm ci` and `npm run dev`, then refresh the browser. No backend changes or credential setup are needed for the theme toggle.


## What changed

- Professional workspace layout with Overview, Purchase Review, Compare Offers, Payments, Analytics Studio, Developer and Connection Settings pages.
- Assessment activity chart, risk distribution chart, agent score indicators and offer price comparison chart.
- Searchable assessment/payment tables, payment audit timeline, integration configuration cards and PayPal authentication check.
- Lazy-loaded AG Studio editor so the main dashboard does not download the entire analytics package immediately.
- Checkout sends the chosen language in PayPal's order experience context and adds a language hint to the approval URL.
- If you select another language for an existing open order, the API returns an explicit conflict rather than silently reusing the old language or creating a duplicate payment.

## Apply the update

1. Stop both terminals with Control + C.
2. Back up your current project folder.
3. Extract the new ZIP separately; do not overwrite your environment files.
4. Copy `backend/app` and `backend/tests` from the new ZIP into your existing `backend`, replacing those folders.
5. Copy `frontend/src`, `frontend/package.json` and `frontend/package-lock.json` into your existing `frontend`, replacing those items.
6. Keep your existing `backend/.env`, `frontend/.env`, virtual environment and database.
7. From your existing `backend` folder run:

```bash
.venv/bin/python -m uvicorn app.main:create_app --factory --reload --port 8000
```

8. In a second terminal, from your existing `frontend` folder run:

```bash
npm ci
npm run dev
```

9. Open http://localhost:5173. Click **Connect API**, enter `TRUSTPAY_API_KEY` and click **Connect workspace**.
10. Start a **New review**, assess the listing and choose the desired PayPal checkout language before creating the order.

The API key remains in memory; re-enter it after a browser reload or PayPal return. Public config is checked first so opening a protected workspace no longer immediately produces unauthorized analytics requests.

## English still appears as Arabic on PayPal?

The application requests `en-US` in the PayPal API and `locale.x=en_US` in the redirect link. The latter is an additional hosted-page hint, not a guarantee that PayPal overrides every logged-in account preference. Arabic uses `ar-AE` / `ar_AE`; French uses `fr-FR` / `fr_FR`.

- Start a fresh assessment. An already-created PayPal order keeps its original experience.
- Do not approve a second test payment for an order you already paid; use the Payments page to inspect it.
- If a fresh order still shows Arabic, test the app in a private browser window, reconnect the access key, choose English, and log into the sandbox buyer when prompted.
- Check the selected language shown beside the order in the purchase details. Your PayPal account language/region can still influence the hosted page.
- We cannot change PayPal's own page styling from TrustPay. This redesign applies to TrustPay's pages.

Official locale behavior: https://developer.paypal.com/api/codes/locale/

## Charts and metrics

All dashboard figures come from the most recent 100 stored assessments. The seven-day activity chart uses UTC day boundaries. Different currency totals are kept separate. Completed-payment totals exclude refunded/reversed records. AI success means assessments report `ai_status: ok`; it is not an accuracy claim. Price comparisons show only offers matching the selected currency and do not convert currencies. No fixture or invented transactions are bundled into the running app.

## Checks

Run backend checks with `python -m pytest` from backend. Run frontend aggregation checks with `npm test` and the production build with `npm run build` from frontend.

Live PayPal-hosted language behavior still requires an account-backed sandbox test. The local regression suite verifies the request locale, redirect hint, preserved order token and language-conflict behavior without moving money.
