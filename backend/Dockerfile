FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    cmake \
    libgeos-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

ENV GEOS_CONFIG=/usr/bin/geos-config

# Install application dependencies
COPY --chown=pwuser:pwuser requirements.txt .
RUN pip install -U setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code with correct ownership
COPY --chown=pwuser:pwuser . .

# Switch to non-root user (pwuser is pre-created in the base image)
USER pwuser

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5200"]
