FROM python:3.11-slim-bookworm

WORKDIR /app

# Pin browser path so --env-file can never override it at runtime
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install base utilities needed before playwright deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies (includes playwright==1.40.0)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's Chromium + all required system libraries in one step
# Browsers land at /ms-playwright/ (set above)
RUN playwright install chromium --with-deps

# Copy application code
COPY app ./app

# Expose port
EXPOSE 8001

# Run the application with root-path for subpath hosting
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--root-path", "/affordabilityassessment"]
