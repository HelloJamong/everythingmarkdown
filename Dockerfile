# Integrated web service image (linux/amd64). Public on Docker Hub: no secrets, .env, or data in any layer.
# HTTPS is terminated by a reverse proxy; this image serves HTTP on 8000 only.

FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim
RUN useradd --system --uid 10001 --user-group --home-dir /nonexistent --no-create-home app \
 && mkdir -p /data /logs && chown app:app /data /logs
COPY --from=build /app/.venv /app/.venv
COPY LICENSE docs/third-party-licenses.md /usr/share/doc/everythingmarkdown/
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data LOG_DIR=/logs
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]
# --proxy-headers trusts X-Forwarded-* only from FORWARDED_ALLOW_IPS (uvicorn default 127.0.0.1).
CMD ["uvicorn", "--factory", "everythingmarkdown.web.app:create_app", \
     "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
