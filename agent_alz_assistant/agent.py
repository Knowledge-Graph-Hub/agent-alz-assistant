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

    async def chat(self, query: str, history: List = None, on_output=None) -> str:
        """
        Send a query to Claude Code CLI and get response

        Args:
            query: User's question/request
            history: Conversation history (optional, not used yet)
            on_output: Optional async callback to receive streaming output line by line

        Returns:
            Claude's response as a string
        """
        # Build command
        # NOTE: Not using --print so we can see intermediate tool calls
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
        ]

        # Add MCP config if it exists
        if self.mcp_config_path.exists():
            cmd.extend(["--mcp-config", str(self.mcp_config_path)])

        # Run Claude CLI from the project root (where CLAUDE.md is)
        project_root = Path(__file__).parent.parent
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
            cwd=str(project_root),  # Run from project root so CLAUDE.md is found
        )

        # Send query and close stdin
        process.stdin.write(query.encode())
        process.stdin.close()
        await process.stdin.wait_closed()

        # Stream output
        stdout_lines = []
        stderr_lines = []
        
        async def read_stdout():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode()
                stdout_lines.append(decoded)
                if on_output:
                    await on_output(decoded)
        
        async def read_stderr():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                decoded = line.decode()
                stderr_lines.append(decoded)
                # Send stderr to callback too (verbose output goes here)
                if on_output:
                    await on_output(decoded)
        
        # Read both streams concurrently
        await asyncio.gather(read_stdout(), read_stderr())
        
        # Wait for process to finish
        await process.wait()

        # Check for errors
        if process.returncode != 0:
            error_msg = ''.join(stderr_lines) if stderr_lines else "Unknown error"
            raise RuntimeError(f"Claude CLI failed: {error_msg}")

        # Return response
        response = ''.join(stdout_lines).strip()
        return response
