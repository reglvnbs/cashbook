FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CASHBOOK_DATABASE_PATH=/app/data/cashbook.db \
    CASHBOOK_LOG_FILE=/app/data/logs/cashbook.log

WORKDIR /app
RUN groupadd --system cashbook && useradd --system --gid cashbook --home-dir /app cashbook
COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt
COPY app ./app
COPY config.json wsgi.py ./
RUN mkdir -p /app/data/logs && chown -R cashbook:cashbook /app

USER cashbook
VOLUME ["/app/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)" || exit 1
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "--graceful-timeout", "30", "wsgi:app"]

