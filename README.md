AI Social Media Post Generator is a web application that helps marketers and content creators generate marketing-grade prompts, captions, hashtags, and AI-powered images for social media posts.

## The Problem

Creating engaging social media content requires significant time and creative effort. Marketers often struggle to consistently produce high-quality prompts for image generation, craft compelling captions, and generate relevant hashtags that increase post visibility.

## The Solution

This application provides an integrated pipeline that transforms simple ideas into polished social media content. Users input a basic concept, and the system enhances it with marketing context, generates professional captions with strategic hashtags, and produces AI-generated images.

## Technology Stack

### Backend (FastAPI)
- **Language**: Python 3.11
- **Framework**: FastAPI 0.115.11
- **AI/ML**: Hugging Face Inference API
  - Text: `google/flan-t5-large`
  - Image: `stabilityai/stable-diffusion-xl-base-1.0`
- **Storage**: Local JSON + PNG files
- **Monitoring**: Prometheus metrics

### Frontend (React + Vite)
- **Framework**: React 19.2.4
- **Build Tool**: Vite 8.0.4
- **UI**: Custom CSS (dark theme)

### Client App (Streamlit)
- Python-based UI alternative

## Quick Start

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn api_gateway.main:app --reload
# API docs at http://127.0.0.1:8000/docs
```

### 2. React Frontend
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### 3. Streamlit Client
```bash
streamlit run streamlit_app.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with HF diagnostics |
| POST | `/enhance-prompt` | Enhance prompt with marketing context |
| POST | `/generate-caption` | Generate caption + hashtags |
| POST | `/generate-images` | Generate AI images |
| POST | `/generate-post` | Full pipeline (all in one) |
| GET | `/history` | List all generations |
| DELETE | `/delete/{id}` | Delete a generation |

## Configuration

Edit `backend/.env`:
```
HF_TOKENS=your_huggingface_token_here
```

## Features

- Prompt enhancement with marketing context
- Caption generation with hashtag extraction
- AI image generation (SDXL)
- Multiple image sizes (1:1, 4:5, 16:9)
- Generation history with view/delete
- Offline fallback mode
- Dark themed UI
