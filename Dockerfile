# ============================================================================
# Stage 1: Builder - Build Python wheels with all build dependencies
# ============================================================================
FROM python:3.10-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies (gcc, g++, cmake for compiling C extensions)
# These are NOT included in the final image
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        cmake \
        pkg-config \
        libgl1-mesa-dev \
        libglib2.0-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and build all wheels
# Building wheels in a separate stage allows us to cache them and avoid
# shipping build tools (gcc, cmake) to the final Lambda image
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip==24.0 setuptools==69.5.1 wheel==0.43.0 && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt && \
    pip wheel --no-cache-dir --wheel-dir /wheels awslambdaric

# ============================================================================
# Stage 2: Runtime - Minimal image with only runtime dependencies
# ============================================================================
FROM python:3.10-slim-bookworm

WORKDIR /var/task

# Install ONLY runtime dependencies (no build tools like gcc)
# This significantly reduces the final image size (~300-400MB savings)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
        libgl1-mesa-glx \
        libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    find /usr/lib -name "*.a" -delete && \
    find /usr/lib -name "*.la" -delete

# Copy pre-built wheels from builder stage
COPY --from=builder /wheels /wheels

# Install all Python packages from wheels (much faster than building from source)
# Using --no-index ensures we only install from our pre-built wheels
RUN pip install --no-cache-dir --upgrade pip==24.0 && \
    pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl && \
    rm -rf /wheels /root/.cache/pip

# Copy application code LAST for better Docker layer caching
# Changes to app code won't invalidate dependency layers
COPY ./app ./app

# Set environment variables
ENV PYTHONPATH="${PYTHONPATH}:/var/task" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Pre-compile Python bytecode for faster Lambda cold starts
# -q: quiet mode
# This compiles .py → .pyc at build time instead of at runtime
RUN python -m compileall -q /var/task/app && \
    find /var/task/app -type d -name "__pycache__" -exec chmod 755 {} \;

# Lambda runtime entrypoint
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["app.main.handler"]