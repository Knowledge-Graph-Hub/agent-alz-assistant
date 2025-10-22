# agent-alz-assistant

Agentic AI assistant for Alzheimer's disease research with literature retrieval and knowledge synthesis

## Overview

This is an agentic AI assistant built with:
- **NiceGUI** for the web interface
- **Claude Code CLI** for agentic orchestration
- **CBORG API** (LBL proxy for accessing AI models)
- **artl-mcp** for scientific literature retrieval
- **mcp-server-fetch** for web content fetching

## Setup

### Prerequisites

**Required Software:**
- **Node.js 18+** (for Claude Code CLI)
- **Python 3.10+** with `uv` package manager
- **Claude Code CLI** (installed globally via npm)

**Required Data:**
You need access to the indexed PaperQA corpora:
- Paper corpus directory (e.g., `~/curategpt/data/alz_papers_1k_text/`)
- PaperQA index directory (usually in `.pqa/indexes/` after indexing)

### Installation

1. **Install Node.js and Claude Code CLI** (if not already installed):
   ```bash
   # Install Node.js (Ubuntu/Debian)
   curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
   sudo apt-get install -y nodejs

   # Install Claude Code CLI
   sudo npm install -g @anthropic-ai/claude-code
   ```

2. Install Python dependencies:
   ```bash
   uv sync
   ```

3. **IMPORTANT: Configure environment variables**:

   **All configuration uses `.env` file** (NOT `mcp_config.json` for secrets):

   ```bash
   cp .env.example .env
   # Edit .env with your settings - this file contains ALL secrets and paths
   ```

   **Required variables in `.env`**:
   - `PORT`: Port to run the application on (default: 8602 for agent.alzassistant.org)
   - `PQA_HOME`: Absolute path to your paper corpus directory
   - `PQA_INDEX`: Absolute path to your PaperQA index directory
   - `OPENAI_API_KEY`: Your OpenAI API key (required for PaperQA)
   - `APP_PASSWORD_HASH`: Bcrypt hash for login password
   - `STORAGE_SECRET`: Secret for encrypting session cookies (change in production)
   - `ANTHROPIC_AUTH_TOKEN`: Your CBORG API key

   **How environment variables work**:
   - The `.env` file is loaded by `app.py` at startup using `python-dotenv`
   - All environment variables are inherited by child processes (including MCP servers and Claude CLI)
   - The Claude Code CLI subprocess inherits `ANTHROPIC_AUTH_TOKEN` from the environment
   - `mcp_config.json` only defines which MCP servers to run, NOT secrets
   - This ensures ONE source of truth for all configuration

   **How Claude authentication works**:
   - The app spawns Claude Code CLI as a subprocess
   - Claude CLI reads `ANTHROPIC_AUTH_TOKEN` from environment variables
   - This token is used to authenticate with the CBORG API
   - The `.env` file provides this token to the subprocess environment

   **To generate a new password hash**:
   ```bash
   python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
   ```

4. **IMPORTANT: Configure MCP servers** (defines which servers to load, uses env vars from `.env`):
   ```bash
   cp mcp_config.json.example mcp_config.json
   # Edit the --directory path in the paperqa server config to point to your installation
   # Example: "/Users/yourname/PythonProject/agent-alz-assistant" or "/home/ubuntu/agent-alz-assistant"
   ```

   **The application will NOT work without this file!** The `query_papers` tool requires the MCP server to be configured.

5. Customize the agent (optional):
   - Edit `CLAUDE.md` to modify the system prompt
   - Edit `mcp_config.json` to add/remove MCP servers

## Running

### Using Make (recommended)

```bash
make start
```

Or for other commands:
```bash
make help      # Show all available commands
make stop      # Stop the application
make restart   # Restart the application
```

### Direct Python execution

```bash
uv run python app.py
```

Then open your browser to the configured port (default: http://localhost:8602)

## Customization

### Adding MCP Servers

Edit `mcp_config.json`:

```json
{
  "mcpServers": {
    "my-tool": {
      "command": "uvx",
      "args": ["my-mcp-server"]
    }
  }
}
```

### Modifying the System Prompt

Edit `CLAUDE.md` to change how the agent behaves.

## Development

### Using Make (recommended)

```bash
make test      # Run tests
make lint      # Lint code
make format    # Format code
make clean     # Clean temporary files
```

### Manual commands

Run tests:
```bash
uv run pytest
```

Lint code:
```bash
uv run ruff check .
```

Format code:
```bash
uv run ruff format .
```

## Deployment

The application is configured to run on port 8602 for deployment to agent.alzassistant.org (proxied through Cloudflare).

**Deployment checklist**:
1. Ensure `.env` file is properly configured on the server with production values
2. Set `STORAGE_SECRET` to a random string (not the example value)
3. Set `APP_PASSWORD_HASH` to a strong password hash
4. Verify `PORT=8602` in `.env`
5. Run `make start` to start the application

## License

BSD-3-Clause

## Author

Justin Reese <justinreese@lbl.gov>
