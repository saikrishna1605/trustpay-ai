# Multi-stage: Vite dashboard → FastAPI serves /api and the built SPA (same origin).
FROM node:22-slim AS dashboard
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_AG_STUDIO_LICENSE_KEY
ENV VITE_AG_STUDIO_LICENSE_KEY=$VITE_AG_STUDIO_LICENSE_KEY
# Leave VITE_API_BASE_URL unset so the SPA calls same-origin /api (Fly Path A / Docker).
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=dashboard /frontend/dist /app/frontend_dist
ENV TRUSTPAY_DB=/data/trustpay.db \
    PORT=8080 \
    PYTHONUNBUFFERED=1
RUN mkdir -p /data
EXPOSE 8080
# Fly http_service.internal_port and Render $PORT both work: default 8080, override via PORT.
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT','8080'), timeout=4)"
CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}"]
