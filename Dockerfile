# Use the official Python image (slim version) as the base image
FROM python:3.14-slim

# Install system dependencies including cron
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    cron \
    file \
    libmagic1 \
    libmagic-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
# WORKDIR /app
WORKDIR /

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app app

# Expose the port
EXPOSE 8000

# rely on docker compose to run command for now

# CMD [ "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" ]