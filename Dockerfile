FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin vortex \
    && mkdir -p /data \
    && chown -R vortex:vortex /app /data

COPY --chown=vortex:vortex . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Deliberately stay as root here: the entrypoint needs root to chown /data
# (which Railway/other platforms remount as root-owned on every start)
# before it drops privileges to the non-root "vortex" user. Do not add
# `USER vortex` — that would defeat the entrypoint's ability to fix
# permissions and reintroduce the "unable to open database file" crash.

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3).read()" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "main.py"]
