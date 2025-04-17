FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

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

# Copy startup script to a location that won't be overwritten by volume mounts
COPY --chown=pwuser:pwuser startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

# Copy application code with correct ownership
COPY --chown=pwuser:pwuser . .

# Switch to non-root user (pwuser is pre-created in the base image)
USER pwuser

# Set the startup script as the entrypoint
ENTRYPOINT ["/usr/local/bin/startup.sh"]

# Default command (passed as arguments to the entrypoint)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5200"]
