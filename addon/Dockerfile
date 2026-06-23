# My Kitchen — Home Assistant add-on image.
# Same runtime recipe as the standalone 7a Dockerfile, but the app is CLONED
# from GitHub at build time (the add-on build context is THIS folder, not the
# repo root, so COPY of the app is impossible). Bumping `version` in config.yaml
# changes BUILD_VERSION, which busts the clone layer cache and re-fetches main.
FROM python:3.12-slim

ARG BUILD_ARCH
ARG BUILD_VERSION

# Required HA labels (we don't use HA's GitHub builder action).
# NOTE: the Jun-2026 docs show io.hass.type="app"; "addon" has years of
# acceptance. If image validation fails on install, swap this one value.
LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="addon" \
  io.hass.arch="aarch64|amd64"

# Same deps as standalone: gosu (root->appuser drop), sqlite3 (WAL-safe backup),
# plus git to fetch the app at build time.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu sqlite3 git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=wsgi:app \
    MY_KITCHEN_PORT=8000 \
    MY_KITCHEN_DB_PATH=/data/my_kitchen.db

WORKDIR /app

# Fetch the app. Referencing BUILD_VERSION in the RUN busts the cache per release.
ARG MY_KITCHEN_REPO=https://github.com/amiablealex/my-kitchen
RUN echo "Building My Kitchen ${BUILD_VERSION}" \
    && git clone --depth 1 --branch main "${MY_KITCHEN_REPO}" /app

RUN pip install -r requirements.txt

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('MY_KITCHEN_PORT','8000')+'/healthz', timeout=4).getcode()==200 else 1)"

# Reuse the SAME entrypoint as standalone. It detects HA via /data/options.json,
# bootstraps options->env + SECRET_KEY, then migrates and starts gunicorn.
ENTRYPOINT ["/app/entrypoint.sh"]
