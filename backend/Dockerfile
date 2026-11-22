# Chromium и системные зависимости Playwright уже в образе (Jammy).
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG NUCLEI_VERSION=3.3.7
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    curl \
    unzip \
    && curl -sL "https://github.com/projectdiscovery/nuclei/releases/download/v${NUCLEI_VERSION}/nuclei_${NUCLEI_VERSION}_linux_amd64.zip" \
      -o /tmp/nuclei.zip \
    && unzip -o /tmp/nuclei.zip nuclei -d /usr/local/bin \
    && chmod +x /usr/local/bin/nuclei \
    && rm -f /tmp/nuclei.zip \
    && nuclei -update-templates -silent \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]