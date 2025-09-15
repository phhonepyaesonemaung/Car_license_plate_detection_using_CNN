# Use an official Python runtime as a parent image


# Use official Python base image for maximum portability
FROM python:3.9-slim

# Install system build tools and libraries for scientific Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app


# Copy backend files
COPY backend/ ./backend/
# Copy frontend templates into backend/templates
COPY frontend/templates/ ./backend/templates/

# Set working directory to backend
WORKDIR /app/backend


# Install dependencies (prefer binary wheels)
RUN pip install --upgrade pip \
    && pip install --prefer-binary -r requirements.txt

# Expose the port your app runs on (change if needed)
EXPOSE 5000

# Set environment variables (optional)
# ENV VAR_NAME=value

# Run the application
CMD ["python", "app.py"]
