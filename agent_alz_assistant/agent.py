"""Claude Code CLI agent orchestrator"""

import asyncio
import os
import subprocess
from pathlib import Path
from typing import List


class ClaudeAgent:
    """Orchestrates Claude Code CLI for agentic behavior"""

    def __init__(self):
        self.mcp_config_path = Path(__file__).parent.parent / "mcp_config.json"
        self.claude_md_path = Path(__file__).parent.parent / "CLAUDE.md"

        # Set up environment for Claude CLI
        self.env = os.environ.copy()

        # CBORG configuration
        api_key_path = Path("~/cborg_alz.key").expanduser()
        if api_key_path.exists():
            self.env["ANTHROPIC_AUTH_TOKEN"] = api_key_path.read_text().strip()
        self.env["ANTHROPIC_BASE_URL"] = "https://api.cborg.lbl.gov"
        self.env["ANTHROPIC_MODEL"] = "anthropic/claude-sonnet"

    async def chat(self, query: str, history: List = None) -> str:
        """
        Send a query to Claude Code CLI and get response

        Args:
            query: User's question/request
            history: Conversation history (optional, not used yet)

        Returns:
            Claude's response as a string
        """
        # Build command
        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
        ]

        # Add MCP config if it exists
        if self.mcp_config_path.exists():
            cmd.extend(["--mcp-config", str(self.mcp_config_path)])

        # Run Claude CLI
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )

        # Send query
        stdout, stderr = await process.communicate(query.encode())

        # Check for errors
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"Claude CLI failed: {error_msg}")

        # Return response
        response = stdout.decode().strip()
        return response
