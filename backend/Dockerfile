# Build from the repo root so the data/ folder is included:
#   docker build -f backend/Dockerfile -t sahaay-backend .
FROM python:3.12-slim-bookworm

# Tesseract with English + Hindi (OCR), Pango (WeasyPrint) and Noto fonts (Devanagari shaping in PDFs).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
      fonts-noto-core fonts-noto-ui-core \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/app ./app
COPY data /app/data

# Secrets (GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SECRET_KEY, CORS_ORIGINS, ...) come from the host's
# environment, never from the image.
ENV PORT=8000
EXPOSE 8000
RUN useradd --create-home app && chown -R app /app
USER app
CMD ["sh", "-c", ".venv/bin/fastapi run app/main.py --host 0.0.0.0 --port ${PORT}"]
