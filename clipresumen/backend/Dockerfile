FROM python:3.12-slim

# Keep Python from buffering stdout/stderr and writing .pyc files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System deps needed by psycopg2 at runtime are covered by the binary wheel,
# but build-essential is occasionally needed for other wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Dev command: hot-reload enabled. Production uses docker-compose.prod.yml (Fase 7).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
