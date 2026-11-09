#!/bin/sh
# Fly [http_service] internal_port is 8080. Default here must match fly.toml / Dockerfile ENV.
# Render (and similar) may inject PORT; Fly sets PORT via fly.toml [env].
set -eu
port="${PORT:-8080}"
echo "trustpay: starting uvicorn on 0.0.0.0:${port}"
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port "${port}"
