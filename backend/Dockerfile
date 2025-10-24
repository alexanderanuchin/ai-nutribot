FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# apt с ретраями + нужные dev-пакеты для gcld3
RUN set -eux; \
    for i in 1 2 3; do \
      apt-get -o Acquire::Retries=5 update && \
      apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        build-essential g++ libprotobuf-dev protobuf-compiler pkg-config git \
        curl ca-certificates \
      && break || (echo "APT failed, retry=$i" && sleep 5); \
    done; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["bash","-lc","./entrypoint.sh"]
