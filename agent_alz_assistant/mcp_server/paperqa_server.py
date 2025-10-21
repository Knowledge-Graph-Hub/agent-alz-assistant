#!/usr/bin/env python
"""MCP server for querying curated Alzheimer's disease papers via PaperQA.

This server provides tools to query the curated paper corpus using the Model Context Protocol.
"""

import asyncio
import json
import os
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from paperqa import Settings
from paperqa.agents.main import agent_query
from paperqa.agents.search import get_directory_index


app = Server("paperqa-server")


async def query_paperqa_corpus(query: str) -> dict:
    """Query PaperQA with the configured corpus.

    Args:
        query: Natural language question about Alzheimer's research

    Returns:
        dict with 'answer' and 'citations' keys
    """

    # Get environment variables - FULL PATHS REQUIRED
    pqa_home = os.environ.get("PQA_HOME")
    if not pqa_home:
        raise ValueError("PQA_HOME environment variable is not set!")

    pqa_index = os.environ.get("PQA_INDEX")
    if not pqa_index:
        raise ValueError("PQA_INDEX environment variable is not set!")

    # Verify PQA_HOME exists
    home_path = Path(pqa_home).expanduser().resolve()
    if not home_path.exists():
        raise ValueError(f"PQA_HOME does not exist: {home_path}")
    if not home_path.is_dir():
        raise ValueError(f"PQA_HOME is not a directory: {home_path}")

    # Verify PQA_INDEX exists
    index_path = Path(pqa_index).expanduser().resolve()
    if not index_path.exists():
        raise ValueError(f"PQA_INDEX does not exist: {index_path}")
    if not index_path.is_dir():
        raise ValueError(f"PQA_INDEX is not a directory: {index_path}")

    # Configure PaperQA settings - match working paperqawrapper.py
    settings = Settings(paper_directory=str(home_path))
    settings.agent.index.name = index_path.name
    settings.agent.index.index_directory = str(index_path.parent)
    
    # Load the index - NEVER build
    try:
        await get_directory_index(settings=settings, build=False)
    except Exception as e:
        error_msg = f"Failed to load index from: {index_path}\n"
        error_msg += f"Error: {e}\n"
        error_msg += f"{pqa_home_var}={home_path}\n"
        error_msg += f"{pqa_index_var}={index_path}\n"
        raise RuntimeError(error_msg) from e
    
    # Run the query
    response = await agent_query(query=query, settings=settings)
    
    # Extract citations from contexts
    # NOTE: We do NOT include DOIs from PaperQA because they may be hallucinated.
    # Only return reliable metadata: PMCID (from filename) and citation text (with caveat).
    citations = []
    seen_docs = set()
    for ctx in response.session.contexts:
        if hasattr(ctx.text, 'doc'):
            doc = ctx.text.doc
            # Avoid duplicates
            if doc.docname not in seen_docs:
                seen_docs.add(doc.docname)
                citation_info = {
                    'key': doc.docname,
                    'citation': doc.citation if hasattr(doc, 'citation') else None,
                    'score': ctx.score,
                    'note': 'Citation text from PaperQA may need verification'
                }
                # Extract PMC ID from filename if available (most reliable metadata)
                if doc.docname.startswith('PMC'):
                    citation_info['pmcid'] = doc.docname.split('_')[0]
                citations.append(citation_info)
    
    return {
        'answer': response.session.answer,
        'citations': citations
    }


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="query_papers",
            description=(
                "Query the curated Alzheimer's disease paper corpus. "
                "This corpus contains high-quality, vetted papers specifically about Alzheimer's disease. "
                "Use this tool FIRST for any Alzheimer's research questions. "
                "The tool returns an answer synthesized from relevant papers along with citations. "
                "IMPORTANT: Always append 'Prioritize recent papers and primary research over reviews.' to your query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language question about Alzheimer's research"
                    }
                },
                "required": ["query"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    if name == "query_papers":
        query = arguments.get("query")
        if not query:
            raise ValueError("query parameter is required")

        try:
            result = await query_paperqa_corpus(query)

            # Return as formatted JSON
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except Exception as e:
            raise RuntimeError(f"Error querying PaperQA: {e}")
    
    raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
