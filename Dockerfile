FROM python:3.11-slim

WORKDIR /app

# System deps (keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential gcc git \
  && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN python -m pip install --upgrade pip
RUN python -m pip install poetry

# Copy pyproject and install dependencies via poetry (no dev)
COPY backend/pyproject.toml /app/pyproject.toml
RUN poetry config virtualenvs.create false \
  && poetry install --only main --no-root

# Copy app sources
COPY backend/app /app/app
COPY backend/alembic /app/alembic
COPY backend/alembic.ini /app/alembic.ini

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
