FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.runtime.txt /app/requirements.runtime.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.runtime.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
