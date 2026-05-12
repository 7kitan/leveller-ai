#!/bin/bash

# Setup Script for AI Inference Hub on GPU Nodes (RunPod, Vast.ai, etc.)
# Optimized for Ubuntu-based PyTorch/CUDA images

echo "--- Starting Setup for AI Inference Hub ---"

# 1. Update System
echo "📦 Installing system dependencies..."
apt-get update && apt-get install -y poppler-utils git coreutils

# 2. Virtual Environment
echo "🐍 Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 3. Upgrade Pip
pip install --upgrade pip

# 4. Install GPU Requirements
echo "📦 Installing Python dependencies (GPU)..."
pip install -r requirements_gpu.txt

# 5. Setup Chandra OCR 2 (Pre-download weights)
echo "🤖 Setting up Chandra OCR 2..."
python setup_chandra.py

# 6. Configuration (Env variables)
if [ ! -f .env ]; then
    echo "⚙️ Creating .env template. Please edit it with your credentials."
    mkdir -p models_cache
    cat <<EOT > .env
AI_INFERENCE_API_KEY=your_secure_api_key_here
PORT=8081
CHANDRA_MODEL_PATH=datalab-to/chandra-ocr-2
BERTSCORE_MODEL_NAME=roberta-large
HF_HOME=./models_cache
TRANSFORMERS_CACHE=./models_cache
EOT
fi

echo "--- Setup Complete ---"
echo ""
echo "Instructions:"
echo "1. Edit the .env file with your AI_INFERENCE_API_KEY."
echo "2. Run the service (Foreground): uvicorn main:app --host 0.0.0.0 --port 8081"
echo "3. Run the service (Background): nohup uvicorn main:app --host 0.0.0.0 --port 8081 > server.log 2>&1 &"
echo "4. Monitor logs: tail -f server.log"
echo "5. Remember to map local port 8081 to a public port on your GPU provider's dashboard."
echo ""
