AI Social Media Post Generator is a web application that helps marketers and content creators generate marketing-grade prompts, captions, hashtags, and AI-powered images for social media posts.

## The Problem

Creating engaging social media content requires significant time and creative effort. Marketers often struggle to consistently produce high-quality prompts for image generation, craft compelling captions, and generate relevant hashtags that increase post visibility. The process of manually refining ideas into marketing-ready content is time-consuming and can be inconsistent in quality.

## The Solution

This application provides an integrated pipeline that transforms simple ideas into polished social media content. Users input a basic concept or topic, and the system enhances it with marketing context, generates professional captions with strategic hashtags, and produces AI-generated images ready for publication.

## Technology Stack

### Backend
- **Language**: Python 3.11
- **Framework**: FastAPI 0.115.11
- **ORM**: SQLAlchemy 2.0.36
- **Database**: PostgreSQL (configured; local file storage in use)
- **AI/ML**: Hugging Face API (Mistral-7B for text generation, Stable Diffusion XL for image generation)

### Frontend
- **Framework**: React 19.2.4
- **Build Tool**: Vite 8.0.4
- **Language**: JavaScript (JSX)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/enhance-prompt` | Enhance user prompt with marketing context |
| POST | `/generate-caption` | Generate caption and hashtags |
| POST | `/generate-images` | Generate AI images |
| POST | `/generate-post` | Full pipeline (enhance + caption + images) |
| GET | `/history` | List all generated posts |
| DELETE | `/delete/{generation_id}` | Delete a generation |

API documentation available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

## Setup

Navigate to the backend directory, create a virtual environment, install dependencies, configure your Hugging Face API token in `.env`, and run the server with `uvicorn api_gateway.main:app --reload`.

## Key Dependencies

- FastAPI, Uvicorn, SQLAlchemy, Pydantic, httpx, huggingface-hub, replicate, loguru, pytest

## Infrastructure Ready

PostgreSQL database, Alembic migrations, Celery/Redis task queue, and Prometheus metrics are available in the stack but require configuration to connect.
