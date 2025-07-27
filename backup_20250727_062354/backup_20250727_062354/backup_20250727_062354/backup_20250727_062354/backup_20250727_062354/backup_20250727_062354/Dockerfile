# Multi-stage build for optimization
FROM rust:1.75 as rust-builder

WORKDIR /app
COPY rust/Cargo.toml rust/Cargo.lock ./rust/
COPY rust/src ./rust/src/

# Build Rust components
WORKDIR /app/rust
RUN cargo build --release

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Rust binaries
COPY --from=rust-builder /app/rust/target/release/ ./rust/target/release/

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs temp monitoring

# Set permissions
RUN chmod +x start_bot.sh

# Health check endpoint
COPY monitoring/health_check.py .
EXPOSE 8080

# Default command
CMD ["python", "elite_mirror_bot.py"]
