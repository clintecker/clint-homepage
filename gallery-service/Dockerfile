FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask \
    pillow \
    boto3 \
    python-slugify \
    gunicorn

# Copy application code
COPY app.py gallery_processor.py ./

# Create non-root user
RUN useradd -m -u 1000 gallery && chown -R gallery:gallery /app
USER gallery

# Expose port
EXPOSE 8080

# Run with gunicorn
# Increased timeout to 300s (5 min) for large gallery uploads
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "300", "--max-requests", "100", "app:app"]
