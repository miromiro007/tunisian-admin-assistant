# Base image: small Python 3.12 (maximum package compatibility).
FROM python:3.12-slim

# Don't write .pyc files; print logs immediately (important for docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Copy requirements FIRST so Docker caches the install layer
# (rebuilds are fast when only your code changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the application code (NOT .env, see .dockerignore).
COPY app ./app

# Run as a non-root user (security best practice).
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# 0.0.0.0 = listen on all interfaces, required inside a container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]