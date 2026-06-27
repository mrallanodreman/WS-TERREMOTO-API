FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gunicorn.conf.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
COPY app ./app

EXPOSE 8000

# ROLE=web (default) | fast | heavy  → ver entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
