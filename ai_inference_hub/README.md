# AI Inference Hub (Chandra OCR 2 & BERTScore)

A lightweight, high-performance AI inference service designed for resource-constrained environments (e.g., VPS with 4 Cores / 8GB RAM). This hub uses a serial queue architecture to process heavy AI tasks without exhausting system memory.

## 🚀 Features
- **Chandra OCR 2**: State-of-the-art document OCR from [Datalab](https://www.datalab.to) (`datalab-to/chandra-ocr-2`). Outputs structured **Markdown** preserving layout, tables, headings, and reading order.
- **4-bit Quantization**: Uses `bitsandbytes` NF4 quantization to run the 5B-param model in ~3-4GB RAM.
- **BERTScore Calculation**: Semantic similarity scoring using contextual embeddings.
- **Async Queue Architecture**: Prevents memory spikes by processing tasks one by one.
- **90+ Language Support**: Vietnamese, English, and 88+ other languages with high accuracy.

## 🛠️ Tech Stack
- **Framework**: FastAPI
- **OCR Model**: `datalab-to/chandra-ocr-2` (Qwen 3.5 based, 5B params, 4-bit quantized)
- **Logic**: Asyncio Queue + Background Workers
- **AI Libraries**: PyTorch, Transformers, chandra-ocr, BERTScore
- **Auth**: API Key via `X-AI-Key` header.

## 📥 Setup Instructions (Ubuntu 22.04)

### 1. System Requirements
- Python 3.10+
- 4 vCPUs / 8GB RAM (minimum)
- `poppler-utils` (for PDF processing)

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd Team078/ai_inference_hub

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements_ai.txt
```

### 3. Environment Variables
Create a `.env` file in this directory:
```env
AI_INFERENCE_API_KEY=your_secret_api_key
PORT=8080
CHANDRA_MODEL_PATH=datalab-to/chandra-ocr-2
BERTSCORE_MODEL_NAME=roberta-large

# Low-RAM (8GB) CPU Optimization
HF_LOCAL_FILES_ONLY=1  # Prevent re-checking Hugging Face Hub if already downloaded
EOT
```

> [!TIP]
> **Stability Tip for 8GB RAM**: 
> Chandra OCR 2 (5B) is heavy. Even with 4-bit quantization, you should ensure your system has at least **8GB-16GB of Swap memory** to prevent `SIGKILL` during the initial loading phase.
> ```bash
> # Create a 16GB swap file (Ubuntu)
> sudo fallocate -l 16G /swapfile
> sudo chmod 600 /swapfile
> sudo mkswap /swapfile
> sudo swapon /swapfile
> ```

### 4. Running the Service
```bash
# Local development
uvicorn main:app --host 0.0.0.0 --port 8080

# Production (using PM2)
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8080" --name ai-hub
```

### 5. GPU Deployment (RunPod / Vast.ai)
For high-performance OCR on GPU nodes:
```bash
# Run the automated setup script
chmod +x setup_gpu_node.sh
./setup_gpu_node.sh
```

## 🚥 API Reference

### OCR Task (Supports PDF & Images)
- **POST** `/tasks/ocr`
- **Body**: 
  ```json
  {
    "file_base64": "...", 
    "file_ext": ".pdf"
  }
  ```
  *(Or use `image_base64` for single images)*
- **Response**: `{"task_id": "...", "status": "pending"}`

### BERTScore Task
- **POST** `/tasks/bertscore`
- **Body**: `{"cv_skills": ["Python", "React"], "jd_skill": "Advanced Python Development"}`
- **Response**: `{"task_id": "...", "status": "pending"}`

### Check Task Status
- **GET** `/tasks/{task_id}`
- **Response**:
  ```json
  {
    "task_id": "...",
    "status": "completed",
    "result": {
      "text": "# Structured Markdown output...\n## Skills\n- Python\n- React\n...",
      "metadata": {
        "total_pages": 2,
        "engine": "chandra-ocr-2",
        "output_format": "markdown"
      }
    }
  }
  ```

## 📊 Output Format
Chandra OCR 2 outputs **structured Markdown** that preserves:
- Heading hierarchy (`#`, `##`, `###`)
- Tables with proper formatting
- Bullet lists and numbered lists
- Reading order across multi-column layouts
- Page markers (`<!-- PAGE X / Y -->`) for multi-page documents

This structured output is significantly better for downstream LLM parsing compared to raw text.

## ⚖️ License
Apache-2.0
