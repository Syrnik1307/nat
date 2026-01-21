FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps kept minimal; add build deps only if you hit wheels issues
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching.
# Use requirements.txt to stay aligned with the repo's current dev/prod Django version.
COPY teaching_panel/requirements.txt /app/teaching_panel/requirements.txt
RUN pip install --no-cache-dir -r /app/teaching_panel/requirements.txt \
    && pip install --no-cache-dir gunicorn

# Copy project
COPY teaching_panel /app/teaching_panel
COPY docker/backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app/teaching_panel

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
