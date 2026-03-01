FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install system Chromium — reliable fallback if Playwright's bundled browser is missing
RUN apt-get update && \
    apt-get install -y --no-install-recommends chromium-browser && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps
# Copy application code
COPY app ./app

# Expose port
EXPOSE 8001

# Run the application with root-path for subpath hosting
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--root-path", "/affordabilityassessment"]