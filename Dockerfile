# Stage 1: Build
FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY locales/ locales/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .[api]

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/src /app/src
COPY --from=builder /app/locales /app/locales
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "cfd.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
