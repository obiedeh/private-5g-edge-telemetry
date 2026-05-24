# Reproducible private 5G telemetry pipeline environment
#
# Build:
#   docker build -t private5g-pipeline:latest .
#
# Run sample pipeline:
#   docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/reports:/app/reports \
#     private5g-pipeline:latest python -m private5g_pipeline.cli \
#     --config configs/pipeline_config.yaml
#
# Run tests:
#   docker run --rm private5g-pipeline:latest python -m pytest -q

FROM python:3.11-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY pyproject.toml ./
COPY private5g_pipeline/ ./private5g_pipeline/
COPY data/ ./data/
COPY configs/ ./configs/

RUN pip install --no-cache-dir -e .

VOLUME ["/app/data", "/app/reports"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import private5g_pipeline" || exit 1

RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["python", "-m", "private5g_pipeline.cli", "--config", "configs/pipeline_config.yaml"]
