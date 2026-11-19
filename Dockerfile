FROM python:3.13-slim

# Copy uv binary from official Astral image
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /bin/uv

# Configure Python and uv environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/srv/.venv/bin:$PATH" \
    PORT=8000

# Set application working directory
WORKDIR /srv

# Create dedicated non-root application user
RUN useradd -r -u 10001 -s /usr/sbin/nologin veritas

# Install dependencies from frozen lockfile for Docker layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application and worker source code
COPY app ./app
COPY worker ./worker

# Ensure file ownership for non-root user
RUN chown -R veritas:veritas /srv

# Switch to non-root execution
USER veritas

# Expose default port
EXPOSE 8000

# Start Uvicorn, evaluating PORT dynamically at container runtime (overridable by Render)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
