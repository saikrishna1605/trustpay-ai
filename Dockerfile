FROM node:22-slim AS dashboard
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_AG_STUDIO_LICENSE_KEY
ENV VITE_AG_STUDIO_LICENSE_KEY=$VITE_AG_STUDIO_LICENSE_KEY
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=dashboard /frontend/dist /app/frontend_dist
ENV TRUSTPAY_DB=/data/trustpay.db
RUN mkdir -p /data
CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
