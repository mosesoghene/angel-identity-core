#!/bin/sh
set -e

# Define the URL and the output directory
MODEL_URL="https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
OUTPUT_DIR="./models"
ZIP_FILE="buffalo_l.zip"

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Download the model zip file
echo "Downloading model from $MODEL_URL..."
if command -v wget >/dev/null 2>&1; then
    wget -O "$ZIP_FILE" "$MODEL_URL"
elif command -v curl >/dev/null 2>&1; then
    curl -L -o "$ZIP_FILE" "$MODEL_URL"
else
    echo "Error: neither wget nor curl is installed." >&2
    exit 1
fi

# Check if unzip is installed
if ! command -v unzip >/dev/null 2>&1; then
    echo "Error: unzip is not installed. Trying to install it..."
    # Assuming a Debian-based image (like python:3.9-slim)
    if [ -f /etc/debian_version ]; then
        apt-get update && apt-get install -y unzip
    else
        echo "Cannot determine package manager to install unzip. Please install it manually in your Dockerfile."
        exit 1
    fi
fi

# Unzip the model into the target directory
echo "Extracting model to $OUTPUT_DIR..."
unzip -o "$ZIP_FILE" -d "$OUTPUT_DIR"

# Remove the downloaded zip file
rm "$ZIP_FILE"

echo "Model downloaded and extracted successfully."
