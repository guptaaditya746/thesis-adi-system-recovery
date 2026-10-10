FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ripgrep findutils grep sed && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
