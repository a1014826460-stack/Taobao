FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
COPY backend ./backend
COPY src ./src
COPY tests ./tests
RUN pip install --no-cache-dir .
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
