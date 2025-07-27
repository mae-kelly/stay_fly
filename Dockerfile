# Elite Alpha Mirror Bot - Production Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for high-performance components
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Rust dependencies
COPY rust/Cargo.toml rust/Cargo.lock rust/
RUN cd rust && cargo fetch

# Copy source code
COPY . .

# Build Rust components for maximum performance
RUN cd rust && cargo build --release

# Create necessary directories
RUN mkdir -p data logs data/backups

# Set up proper permissions
RUN chmod +x scripts/setup/* scripts/monitoring/*

# Install Python dependencies in production mode
RUN pip install --no-cache-dir --no-dev -r requirements.txt

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose ports
EXPOSE 8080 8081

# Environment variables
ENV PYTHONPATH=/app
ENV RUST_BACKTRACE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd -m -u 1000 elitebot && chown -R elitebot:elitebot /app
USER elitebot

# Default command
CMD ["python", "core/master_coordinator.py"]

# Production optimizations
LABEL org.opencontainers.image.title="Elite Alpha Mirror Bot"
LABEL org.opencontainers.image.description="Real-time elite wallet mirror trading system"
LABEL org.opencontainers.image.version="2.0"
LABEL org.opencontainers.image.authors="Elite Trading Systems"