# Backend - AI Social Media Post Generator

This backend is built with FastAPI and follows the architecture in `docs/BACKEND.md`.

## Features

- `POST /enhance-prompt`
- `POST /generate-caption`
- `POST /generate-images`
- `POST /generate-post`
- `GET /history`
- `DELETE /delete/{generation_id}`
- `GET /health`

## Setup

1. Activate your virtual environment.
2. Install dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

3. Copy env file:

   ```bash
   copy backend\.env.example backend\.env
   ```

4. Run API:

   ```bash
   cd backend
   uvicorn api_gateway.main:app --reload
   ```

Swagger docs are available at:

- `http://127.0.0.1:8000/docs`

## Output Storage

- Images: `backend/outputs/images`
- Metadata JSON: `backend/outputs/json`

If `HUGGINGFACE_API_KEY` is not set, the API still works in offline mode using local fallback text and preview image generation.
