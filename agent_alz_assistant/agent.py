"""Claude Code CLI agent orchestrator"""

import asyncio
import os
import subprocess
import uuid
from pathlib import Path
from typing import List


class ClaudeAgent:
    """Orchestrates Claude Code CLI for agentic behavior"""

    def __init__(self):
        self.mcp_config_path = Path(__file__).parent.parent / "mcp_config.json"
        self.claude_md_path = Path(__file__).parent.parent / "CLAUDE.md"

        # Generate a unique session ID for this conversation
        self.session_id = str(uuid.uuid4())
        self.is_first_message = True  # Track if this is the first message

        # Set up environment for Claude CLI
        # Environment variables are already loaded from .env by app.py
        # Just copy the current environment (which includes .env vars)
        self.env = os.environ.copy()

    async def chat(self, query: str, history: List = None, on_output=None) -> str:
        """
        Send a query to Claude Code CLI and get response

        Args:
            query: User's question/request
            history: Conversation history (optional, maintained via session_id)
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

        # For first message: use --session-id to create session
        # For subsequent messages: use --resume to continue the session
        if self.is_first_message:
            cmd.extend(["--session-id", self.session_id])
            self.is_first_message = False
        else:
            cmd.extend(["--resume", self.session_id])

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
