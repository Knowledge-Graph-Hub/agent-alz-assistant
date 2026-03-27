# Dockerfile for agent-alz-assistant
# Containerizes the Alzheimer's research assistant for isolated execution
#
# Data (papers, KG, index) is mounted as volumes — not copied into the image.
# Secrets come from .env mounted read-only at runtime.

FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 LTS (required for Claude CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI
RUN npm install -g @anthropic-ai/claude-code

# Install uv for fast Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency manifests first (layer caching)
COPY pyproject.toml uv.lock README.md ./

# Stub package so uv can do the editable install
RUN mkdir -p agent_alz_assistant && touch agent_alz_assistant/__init__.py

# Install Python deps — cached until pyproject.toml or uv.lock changes
RUN uv pip install --system -e .

# Copy application source
COPY app.py CLAUDE.md ./
COPY agent_alz_assistant/ agent_alz_assistant/

# Copy Docker-specific MCP config (with /app paths) as mcp_config.json
COPY mcp_config.docker.json mcp_config.json

# Copy subagent configs
COPY subagents/ subagents/

# Create non-root user (Claude CLI refuses --dangerously-skip-permissions as root)
RUN useradd -m -u 1001 appuser

# Create runtime directories and set ownership
RUN mkdir -p logs static/plots .nicegui && chown -R appuser:appuser /app

USER appuser

# Expose NiceGUI port
EXPOSE 8602

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
