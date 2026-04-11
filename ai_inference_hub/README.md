# AI Inference Hub (Chandra OCR & BERTScore)

A lightweight, high-performance AI inference service designed for resource-constrained environments (e.g., VPS with 4 Cores / 8GB RAM). This hub uses a serial queue architecture to process heavy AI tasks without exhausting system memory.

## 🚀 Features
- **Chandra OCR Integration**: High-accuracy document-to-markdown extraction using Vision-Language Models.
- **BERTScore Calculation**: Semantic similarity scoring using contextual embeddings.
- **Async Queue Architecture**: Prevents memory spikes by processing tasks one by one.
- **CPU Optimized**: Pre-configured to run efficiently on CPU using `torch-cpu`.

## 🛠️ Tech Stack
- **Framework**: FastAPI
- **Logic**: Asyncio Queue + Background Workers
- **AI Libraries**: PyTorch (CPU), Transformers, BERTScore
- **Auth**: API Key via `X-API-KEY` header.

## 📥 Setup Instructions (Ubuntu 22.04)

### 1. System Requirements
- Python 3.10+
- 4 vCPUs / 8GB RAM
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
HUB_API_KEY=your_secret_api_key
PORT=8080
```

### 4. Running the Service
```bash
# Local development
uvicorn ai_inference_hub.main:app --host 0.0.0.0 --port 8080

# Production (using PM2)
pm2 start "uvicorn ai_inference_hub.main:app --host 0.0.0.0 --port 8080" --name ai-hub
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
    "result": { "text": "Extracted markdown for all pages..." }
  }
  ```

## ⚖️ License
Apache-2.0
