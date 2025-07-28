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

# Copy sample data for testing
COPY sample_dataset/ ./sample_dataset/

# Create output directory
RUN mkdir -p /app/output

# Set the entrypoint to run the main.py script
ENTRYPOINT ["python", "main.py"]

# Default command arguments - can be overridden
CMD ["sample_dataset/pdfs/*.pdf", "output"] 