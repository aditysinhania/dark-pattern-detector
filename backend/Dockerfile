FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# - gcc: needed to compile some Python packages
# - libpq-dev: PostgreSQL client library for psycopg2
# - curl: needed for healthchecks
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies FIRST
# Docker layer caching: if requirements.txt doesn't change,
# this layer is reused — much faster rebuilds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# Expose port
EXPOSE 8000

# Default command (overridden by docker-compose for dev)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]