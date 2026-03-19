FROM python:3.11-slim
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy package source and set PYTHONPATH
COPY src/ /app/src/
COPY config/ /app/config/
ENV PYTHONPATH=/app/src

ENTRYPOINT ["python", "-m", "tayfin_screener_jobs.cli.main"]
CMD ["jobs", "list"]
