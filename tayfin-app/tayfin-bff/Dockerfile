FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY config/ config/

ENV PYTHONPATH=/app/src

EXPOSE 8030

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8030/health')"

CMD ["flask", "--app", "tayfin_bff.app", "run", "--host", "0.0.0.0", "--port", "8030"]
