# ---------- Stage 1: Builder ----------
FROM python:3.11-slim AS builder

# Install system dependencies needed for psycopg2 and building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential gcc libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies into /install
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder stage
COPY --from=builder /install /usr/local

COPY . .

EXPOSE 8010

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
