# Multi-stage production container for ORIGIN research platform & Lab UI
# Stage 1: Build Next.js Lab UI
FROM node:24-slim AS ui-builder
WORKDIR /app/lab
COPY apps/lab/package*.json ./
RUN npm ci --prefer-offline
COPY apps/lab/ ./
RUN npm run build

# Stage 2: Python environment with PyBullet and ORIGIN
FROM python:3.12-slim AS runner
WORKDIR /origin

# System dependencies for PyBullet compilation & runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy Python project definition
COPY pyproject.toml README.md ./
COPY packages/ ./packages/

# Install origin with all dependencies including embodied (PyBullet) and dev tooling
RUN uv pip install --system -e ".[all]"

# Copy Lab UI from ui-builder
COPY --from=ui-builder /app/lab /origin/apps/lab

# Copy configuration and scripts
COPY configs/ ./configs/
COPY scripts/ ./scripts/

# Volumes for persistent store
VOLUME ["/origin/runs"]

# Expose ports: 8788 for API, 4317 for Lab UI
EXPOSE 8788 4317

ENV ORIGIN_STORE=/origin/runs
ENV NEXT_PUBLIC_ORIGIN_API=http://127.0.0.1:8788

# Default command: show doctor diagnostics and launch api
CMD ["sh", "-c", "origin-doctor --store /origin/runs && origin-api --store /origin/runs --host 0.0.0.0 --port 8788"]
