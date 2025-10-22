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

You need access to the indexed PaperQA corpora. These are located at:
- `~/curategpt/data/alz_papers_1k_text/`

And also a paperqa index directory (sometimes located in .pqa/indexes/ if you indexed using paperqa)

### Installation

1. Install dependencies:
   ```bash
   uv sync
   ```

2. **IMPORTANT: Configure environment variables**:

   **All configuration uses `.env` file** (NOT `mcp_config.json` for secrets):

   ```bash
   cp .env.example .env
   # Edit .env with your settings - this file contains ALL secrets and paths
   ```

   **Required variables in `.env`**:
   - `PQA_HOME`: Absolute path to your paper corpus directory
   - `PQA_INDEX`: Absolute path to your PaperQA index directory
   - `OPENAI_API_KEY`: Your OpenAI API key (required for PaperQA)
   - `APP_PASSWORD_HASH`: Bcrypt hash for login password (default: demo123)
   - `ANTHROPIC_AUTH_TOKEN`: Your CBORG API key

   **How environment variables work**:
   - The `.env` file is loaded by `app.py` at startup
   - All environment variables are inherited by child processes (including MCP servers)
   - `mcp_config.json` only defines which MCP servers to run, NOT secrets
   - This ensures ONE source of truth for all configuration

   **To generate a new password hash**:
   ```bash
   python -c "import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())"
   ```

3. Configure MCP servers (defines which servers to load, uses env vars from `.env`):
   ```bash
   cp mcp_config.json.example mcp_config.json
   # Edit the --directory path to point to your installation
   ```

4. Alternative: Use CBORG key file (optional, can use .env instead):
   ```bash
   echo "your-cborg-key" > ~/cborg_alz.key
   ```

4. Customize the agent (optional):
   - Edit `CLAUDE.md` to modify the system prompt
   - Edit `mcp_config.json` to add/remove MCP servers

## Running

```bash
python app.py
```

Then open your browser to http://localhost:8080

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

## License

BSD-3-Clause

## Author

Justin Reese <justinreese@lbl.gov>
