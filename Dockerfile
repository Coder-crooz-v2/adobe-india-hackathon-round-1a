# Dockerfile for Challenge 1a - PDF Structure Extractor
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for PyMuPDF
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application
COPY main.py .

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Copy sample data for testing (optional)
COPY sample_dataset/ ./sample_dataset/

# Set the entrypoint to run the main.py script
ENTRYPOINT ["python", "main.py"]

# Default command arguments - process all PDFs from /app/input to /app/output
CMD ["/app/input/*.pdf", "/app/output"]
