FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
COPY backend ./backend
COPY src ./src
COPY tests ./tests
RUN pip install --no-cache-dir .
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
