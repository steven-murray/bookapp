FROM python:3.11-slim

WORKDIR /app

# Install git and uv
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies system-wide using uv pip
RUN uv pip install --system --no-cache -e .

# Copy application code
COPY . .

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Run database setup and start gunicorn
# Use db.create_all() instead of upgrade-db for Postgres compatibility
CMD python -c "from bookapp.app import app, db; app.app_context().push(); db.create_all(); print('Database ready')" && \
    gunicorn -w 2 -k gthread --timeout 120 -b 0.0.0.0:${PORT:-8080} bookapp.app:app
