FROM python:3.12-slim

WORKDIR /app

# Install deps
COPY requirements.txt .
COPY requirements-docling.txt .
COPY requirements-marker.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Heavy PDF parsers live in isolated virtualenvs to avoid dependency conflicts
# with the main backend environment, especially pypdfium2 versions.
RUN python -m venv /opt/docling-venv \
    && /opt/docling-venv/bin/pip install --no-cache-dir -r requirements-docling.txt
RUN python -m venv /opt/marker-venv \
    && /opt/marker-venv/bin/pip install --no-cache-dir -r requirements-marker.txt

# Runtime libs needed by layout/OCR stacks used by Docling/Marker.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libxcb1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy source — preserve backend/ package structure so imports work
COPY . ./backend/

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
