# Stage 1: Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies, including build tools for compiling packages.
# - build-essential: Installs C/C++ compilers (gcc, g++).
# - cmake: A build tool required by many C++ projects.
# - libgl1: A graphics library required by OpenCV.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libgl1 \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

RUN wget -O "buffalo_l.zip" "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
    

# Copy the dependencies file first to leverage Docker's layer caching.
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies using pip.
RUN pip install --no-cache-dir -r requirements.txt


# Copy the application code into the container
COPY ./app /app/app

# Move the downloaded models to the default insightface location
RUN mkdir -p /root/.insightface && mv ./models /root/.insightface/models

# Expose the port the app runs on
EXPOSE 8000

# Add a health check to ensure the container is running and the service is responsive.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Define the command to run the application using Uvicorn.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
