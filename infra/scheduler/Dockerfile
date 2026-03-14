FROM python:3.11-slim
WORKDIR /app

# Install lightweight deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only the scheduler files (avoid copying the whole repo)
COPY infra/scheduler/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY infra/scheduler /app/

# Ensure run script is executable in the image
RUN chmod +x /app/run_job.sh || true

WORKDIR /app

ENTRYPOINT ["python", "-u", "scheduler.py"]
CMD ["--once"]
