# Slim, multi-arch Python base — resolves to arm64 automatically on the Pi.
FROM python:3.12-slim

# gosu lets the entrypoint start as root (to fix volume ownership) then drop to
# an unprivileged user. zoneinfo data comes from the pip `tzdata` package, so no
# apt tzdata is needed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# Unprivileged runtime user.
RUN useradd --create-home --uid 1000 appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=wsgi:app \
    MY_KITCHEN_PORT=8000 \
    MY_KITCHEN_DB_PATH=/data/my_kitchen.db

WORKDIR /app

# Deps first so this layer caches unless requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code (respecting .dockerignore — no .env, no *.db, no data/).
COPY . .

# Entrypoint runs migrations once, then execs gunicorn.
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# Health probe (slim has no curl). Hits the login-exempt /healthz endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('MY_KITCHEN_PORT','8000')+'/healthz', timeout=4).getcode()==200 else 1)"

ENTRYPOINT ["/app/entrypoint.sh"]
