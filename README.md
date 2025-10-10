# agent-alz-assistant

Agentic AI assistant for Alzheimer's disease research with literature retrieval and knowledge synthesis

## Overview

This is an agentic AI assistant built with:
- **NiceGUI** for the web interface
- **Claude Code CLI** for agentic orchestration
- **CBORG API** (LBL proxy to AWS Bedrock)
- **artl-mcp** for scientific literature retrieval
- **mcp-server-fetch** for web content fetching

## Setup

### Prerequisites

You need access to the indexed PaperQA corpora. These are located at:
- `~/curategpt/data/Bateman_LLM_360/` - Small corpus (360 papers)
- `~/curategpt/data/alz_papers_1k_text/` - Medium corpus (1,065 papers)
- `~/curategpt/data/alz_papers_3k_text/` - Large corpus (3,000 papers)

Each corpus directory must contain a `.pqa/indexes/` subdirectory with the PaperQA indexes.

### Installation

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your API key
   ```

   Or set environment variables:
   ```bash
export ANTHROPIC_AUTH_TOKEN=$(cat ~/cborg_alz.key)
   export ANTHROPIC_BASE_URL=https://api.cborg.lbl.gov
   export ANTHROPIC_MODEL=anthropic/claude-sonnet
   ```

3. Customize the agent:
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
