# PaperMint — Deployment & Operations Manual

## 1. Deployment Overview

PaperMint is designed to deploy seamlessly across two primary target environments:
1. **Streamlit Community Cloud** (SaaS managed cloud for fast sharing).
2. **Containerized Docker Infrastructure** (Self-hosted, Kubernetes, AWS ECS, GCP Cloud Run).

---

## 2. Option A: Streamlit Community Cloud Deployment

### 2.1 Repository Configuration
Ensure the following files are present at the repository root:
* `packages.txt` (Debian system packages):
  ```text
  tesseract-ocr
  tesseract-ocr-eng
  libgl1
  ```
* `pyproject.toml` (Python dependencies with exact version pins):
  Ensure all production dependencies under `[project.dependencies]` are specified.
* `.streamlit/config.toml` (Server configuration):
  ```toml
  [server]
  headless = true
  port = 8501
  maxUploadSize = 50
  enableCORS = false
  enableXsrfProtection = true

  [theme]
  base = "dark"
  primaryColor = "#34D399"
  backgroundColor = "#0F172A"
  secondaryBackgroundColor = "#1E293B"
  textColor = "#F8FAFC"
  font = "sans serif"
  ```

### 2.2 Cold-Start spaCy Language Model Handling
PaperMint includes an automatic fallback in `papermint/parsers/citation_parser.py` and `summarizer.py`:
```python
try:
    _nlp = spacy.load(SPACY_MODEL)
except OSError:
    from spacy.cli import download

    download(SPACY_MODEL)
    _nlp = spacy.load(SPACY_MODEL)
```
This ensures the model downloads automatically on initial boot without failing the deployment.

---

## 3. Option B: Docker Container Deployment

### 3.1 Production Dockerfile Specification
Create a `Dockerfile` in the root directory using a secure, multi-stage, non-root approach:

```dockerfile
# Stage 1: Build & Dependency Resolution
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --user .
RUN python -m spacy download en_core_web_sm

# Stage 2: Minimal Runtime Environment
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install system dependencies (Tesseract OCR for image parsing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged user for security
RUN groupadd -r papermint && useradd -r -g papermint -s /bin/false papermint

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/papermint/.local
ENV PATH=/home/papermint/.local/bin:$PATH

# Copy application source code
COPY . .

RUN chown -R papermint:papermint /app /home/papermint

USER papermint

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 3.2 Docker Build & Run Commands
```bash
# Build the container
docker build -t papermint:latest .

# Run locally
docker run -d -p 8501:8501 --name papermint_app papermint:latest

# Verify health status
docker inspect --format='{{json .State.Health}}' papermint_app
```

---

## 4. Performance & Memory Optimization

1. **PyMuPDF Memory Management**:
   Document streams are opened in-memory using `fitz.open(stream=..., filetype="pdf")` and closed immediately upon completion of text extraction, preventing memory accumulation across large PDF files.
2. **Lazy Model Loading**:
   spaCy language pipelines are loaded as lazily initialized singletons. Memory is allocated once upon first extraction and shared across user sessions.
3. **Max File Size Guardrail**:
   Default max upload limit is set to $50\text{ MB}$ (`MAX_FILE_SIZE_MB = 50`) in `papermint/config.py` and `.streamlit/config.toml` to prevent Denial of Service (DoS) memory exhaustion.
