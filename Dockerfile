# Sefernâme API: FastAPI + Tesseract (passport MRZ). Built by deploy/docker-compose.yml.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UPLOAD_DIR=/data/uploads

# Tesseract reads the passport MRZ; nothing else from the system is needed
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first: this layer is rebuilt only when requirements.txt changes
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Never run as root inside the container; uploads live on a volume owned by this user
RUN useradd --create-home --uid 10001 sefer \
    && mkdir -p /data/uploads \
    && chown -R sefer /data
USER sefer

EXPOSE 8000

# --proxy-headers: the client address comes from Caddy's X-Forwarded-For (the login limit needs it).
# Trusting every forwarder is safe only because this port is never published: Caddy is the one way in.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
