# ─────────────────────────────────────────────────────────────────────────────
# Weather Analytics — API (FastAPI) + frontend (web/, Vite) — spec 006
#
# Multi-stage: stage 1 builda o frontend com Node; stage 2 roda a API em
# Python, com o resultado do build do Vite copiado para api/app/static.
#
# O contexto de build é a RAIZ do repo (não ./api): o stage Node precisa de
# web/ e o stage final precisa de api/.
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-slim AS frontend-build

WORKDIR /web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
# outDir do Vite é ../api/app/static → /api/app/static neste stage
RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ .
COPY --from=frontend-build /api/app/static/ ./app/static/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
