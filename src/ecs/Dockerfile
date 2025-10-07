# Copyright © Amazon.com and Affiliates

FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

RUN apt-get update -y && apt-get install --no-install-recommends -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system appgroup && adduser --system --group appuser

COPY pyproject.toml uv.lock /app/
COPY .streamlit/ /app/.streamlit/

RUN pip3 --no-cache-dir install -U pip
RUN pip3 --no-cache-dir install uv

RUN chown -R appuser:appgroup /app
RUN mkdir -p /home/appuser/.cache && chown -R appuser:appgroup /home/appuser/.cache

USER appuser
ENV UV_CACHE_DIR=/home/appuser/.cache/uv
RUN uv sync --frozen --no-cache --no-dev

COPY src/ /app/src

EXPOSE 8501

HEALTHCHECK CMD ["curl", "--fail", "http://localhost:8501/_stcore/health"]

ENTRYPOINT ["uv", "run", "streamlit", "run", "src/Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
