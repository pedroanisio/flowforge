# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1: Build Pandoc from source using cabal with proper data files
# =============================================================================
FROM haskell:9.8-slim-bullseye as pandoc-builder

# Install system dependencies for building Pandoc
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    zlib1g-dev \
    liblua5.3-dev \
    libffi-dev \
    libgmp-dev \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Update cabal package list
RUN cabal update

# Install pandoc-cli using cabal
RUN cabal install pandoc-cli --install-method=copy --installdir=/usr/local/bin

# Download and install pandoc data files
RUN mkdir -p /usr/local/share/pandoc && \
    cd /tmp && \
    curl -sL https://github.com/jgm/pandoc/archive/refs/tags/3.7.0.2.tar.gz | tar xz && \
    cp -r pandoc-3.7.0.2/data/* /usr/local/share/pandoc/ && \
    rm -rf /tmp/pandoc-3.7.0.2

# Create the cabal store directory structure and link data files dynamically
RUN PANDOC_STORE_PATH=$(find /root/.local/state/cabal/store -type d -path "*/pandoc-3.7.0.2-*/share" | head -n 1) && \
    if [ -n "$PANDOC_STORE_PATH" ]; then \
        ln -s /usr/local/share/pandoc "$PANDOC_STORE_PATH/data"; \
    else \
        echo "Warning: Pandoc store path not found, skipping data file symlink"; \
    fi

# Verify pandoc works with data files
RUN pandoc --version && pandoc --print-default-data-file abbreviations > /dev/null

# =============================================================================
# Stage 2: Main application image
# =============================================================================
FROM python:3.11-slim

# Install Node.js, npm, Docker CLI, and system dependencies for the application
RUN apt-get update && \
    apt-get install -y \
    curl \
    build-essential \
    liblua5.3-0 \
    zlib1g \
    libffi8 \
    libgmp10 \
    ca-certificates \
    gnupg \
    lsb-release \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the built pandoc binary and data files from the builder stage
COPY --from=pandoc-builder /usr/local/bin/pandoc /usr/local/bin/pandoc
COPY --from=pandoc-builder /usr/local/share/pandoc /usr/local/share/pandoc
COPY --from=pandoc-builder /root/.local/state/cabal /root/.local/state/cabal

# Verify pandoc works in the final image
RUN pandoc --version && pandoc --print-default-data-file abbreviations > /dev/null

# Set workdir
WORKDIR /app

# Copy Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app first
COPY . .

# Install Node dependencies
RUN npm install

# Build Tailwind CSS with all files available
RUN npx tailwindcss -i ./app/static/css/src/main.css -o ./app/static/css/dist/main.css --minify

# Create necessary directories for plugin data
RUN mkdir -p /app/data/chains /app/data/templates /app/data/downloads

# Expose FastAPI port
EXPOSE 5000

# Set environment variables for FastAPI/Uvicorn
ENV PYTHONPATH=/app
ENV PANDOC_VERSION=3.7.0.2-with-datafiles

# Health check to ensure pandoc is working with data files
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pandoc --version && pandoc --print-default-data-file abbreviations > /dev/null && curl -f http://localhost:5000/api/plugins || exit 1

# Run FastAPI with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]