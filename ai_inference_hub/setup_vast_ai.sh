#!/bin/bash

# Setup Script for AI Inference Hub on vast.ai
# Tested on vastai/pytorch_cuda-12.1.1-auto/jupyter

echo "--- Starting Setup for AI Inference Hub ---"

# 1. Update System
apt-get update && apt-get install -y poppler-utils git

# 2. Virtual Environment (Optional on vast.ai, but recommended)
python3 -m venv venv
source venv/bin/activate

# 3. Upgrade Pip
pip install --upgrade pip

# 4. Install GPU Requirements
# Using the new requirements_gpu.txt
pip install -r requirements_gpu.txt

# 5. Configuration (Env variables)
if [ ! -f .env ]; then
    echo "Creating .env template. Please edit it with your API keys."
    cat <<EOT > .env
HUB_API_KEY=your_secure_api_key_here
PORT=8080
CHANDRA_MODEL_PATH=datalab-to/chandra-ocr-2
BERTSCORE_MODEL_NAME=microsoft/deberta-base-mnli
EOT
fi

echo "--- Setup Complete ---"
echo "Instructions:"
echo "1. Edit the .env file with your HUB_API_KEY."
echo "2. Run the service: uvicorn main:app --host 0.0.0.0 --port 8080"
echo "3. Remember to map local port 8080 to a public port on vast.ai dashboard."
