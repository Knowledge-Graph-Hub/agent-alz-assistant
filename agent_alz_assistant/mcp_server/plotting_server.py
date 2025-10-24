#!/usr/bin/env python
"""MCP server for creating data visualizations.

This server provides tools to create plots from data using matplotlib and seaborn.
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


app = Server("plotting-server")

# Set seaborn style for consistent, publication-quality plots
sns.set_theme(style="whitegrid", palette="colorblind")


def create_bar_plot(data: list[dict], x: str, y: str, title: str,
                    x_label: str = None, y_label: str = None,
                    hue: str = None) -> Path:
    """Create a bar plot."""
    df = pd.DataFrame(data)

    plt.figure(figsize=(10, 6))
    if hue:
        sns.barplot(data=df, x=x, y=y, hue=hue)
    else:
        sns.barplot(data=df, x=x, y=y)

    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel(x_label or x, fontsize=12)
    plt.ylabel(y_label or y, fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Save with unique filename
    plot_id = str(uuid.uuid4())[:8]
    plot_path = Path("static/plots") / f"plot_{plot_id}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return plot_path


def create_scatter_plot(data: list[dict], x: str, y: str, title: str,
                       x_label: str = None, y_label: str = None,
                       hue: str = None, size: str = None) -> Path:
    """Create a scatter plot."""
    df = pd.DataFrame(data)

    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x=x, y=y, hue=hue, size=size, s=100, alpha=0.7)

    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel(x_label or x, fontsize=12)
    plt.ylabel(y_label or y, fontsize=12)
    plt.tight_layout()

    plot_id = str(uuid.uuid4())[:8]
    plot_path = Path("static/plots") / f"plot_{plot_id}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return plot_path


def create_line_plot(data: list[dict], x: str, y: str, title: str,
                    x_label: str = None, y_label: str = None,
                    hue: str = None) -> Path:
    """Create a line plot."""
    df = pd.DataFrame(data)

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x=x, y=y, hue=hue, marker='o')

    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel(x_label or x, fontsize=12)
    plt.ylabel(y_label or y, fontsize=12)
    plt.tight_layout()

    plot_id = str(uuid.uuid4())[:8]
    plot_path = Path("static/plots") / f"plot_{plot_id}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return plot_path


def create_box_plot(data: list[dict], x: str, y: str, title: str,
                   x_label: str = None, y_label: str = None) -> Path:
    """Create a box plot."""
    df = pd.DataFrame(data)

    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x=x, y=y)

    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel(x_label or x, fontsize=12)
    plt.ylabel(y_label or y, fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    plot_id = str(uuid.uuid4())[:8]
    plot_path = Path("static/plots") / f"plot_{plot_id}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return plot_path


def create_heatmap(data: list[dict], title: str) -> Path:
    """Create a heatmap from matrix data."""
    # Assuming data is a list of dicts representing rows
    df = pd.DataFrame(data)

    plt.figure(figsize=(10, 8))
    sns.heatmap(df, annot=True, fmt=".2f", cmap="coolwarm", center=0)

    plt.title(title, fontsize=14, fontweight='bold')
    plt.tight_layout()

    plot_id = str(uuid.uuid4())[:8]
    plot_path = Path("static/plots") / f"plot_{plot_id}.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return plot_path


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available plotting tools."""
    return [
        Tool(
            name="create_plot",
            description=(
                "Create a data visualization plot. "
                "Supports bar charts, scatter plots, line plots, box plots, and heatmaps. "
                "Use this to visualize data extracted from research papers."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "plot_type": {
                        "type": "string",
                        "enum": ["bar", "scatter", "line", "box", "heatmap"],
                        "description": "Type of plot to create"
                    },
                    "data": {
                        "type": "array",
                        "description": "Array of data objects. Each object should have keys matching x, y, and optional hue/size parameters.",
                        "items": {"type": "object"}
                    },
                    "x": {
                        "type": "string",
                        "description": "Column name for x-axis (required for bar, scatter, line, box)"
                    },
                    "y": {
                        "type": "string",
                        "description": "Column name for y-axis (required for bar, scatter, line, box)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Plot title"
                    },
                    "x_label": {
                        "type": "string",
                        "description": "X-axis label (optional, defaults to x column name)"
                    },
                    "y_label": {
                        "type": "string",
                        "description": "Y-axis label (optional, defaults to y column name)"
                    },
                    "hue": {
                        "type": "string",
                        "description": "Column name for color grouping (optional, for bar/scatter/line)"
                    },
                    "size": {
                        "type": "string",
                        "description": "Column name for point sizes (optional, for scatter only)"
                    }
                },
                "required": ["plot_type", "data", "title"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    if name == "create_plot":
        plot_type = arguments.get("plot_type")
        data = arguments.get("data")
        title = arguments.get("title")

        if not data:
            raise ValueError("data parameter is required")
        if not title:
            raise ValueError("title parameter is required")

        try:
            # Ensure static/plots directory exists
            Path("static/plots").mkdir(parents=True, exist_ok=True)

            # Create the appropriate plot
            if plot_type == "bar":
                x = arguments.get("x")
                y = arguments.get("y")
                if not x or not y:
                    raise ValueError("x and y parameters are required for bar plots")
                plot_path = create_bar_plot(
                    data, x, y, title,
                    arguments.get("x_label"),
                    arguments.get("y_label"),
                    arguments.get("hue")
                )

            elif plot_type == "scatter":
                x = arguments.get("x")
                y = arguments.get("y")
                if not x or not y:
                    raise ValueError("x and y parameters are required for scatter plots")
                plot_path = create_scatter_plot(
                    data, x, y, title,
                    arguments.get("x_label"),
                    arguments.get("y_label"),
                    arguments.get("hue"),
                    arguments.get("size")
                )

            elif plot_type == "line":
                x = arguments.get("x")
                y = arguments.get("y")
                if not x or not y:
                    raise ValueError("x and y parameters are required for line plots")
                plot_path = create_line_plot(
                    data, x, y, title,
                    arguments.get("x_label"),
                    arguments.get("y_label"),
                    arguments.get("hue")
                )

            elif plot_type == "box":
                x = arguments.get("x")
                y = arguments.get("y")
                if not x or not y:
                    raise ValueError("x and y parameters are required for box plots")
                plot_path = create_box_plot(
                    data, x, y, title,
                    arguments.get("x_label"),
                    arguments.get("y_label")
                )

            elif plot_type == "heatmap":
                plot_path = create_heatmap(data, title)

            else:
                raise ValueError(f"Unsupported plot type: {plot_type}")

            # Return success with plot path
            result = {
                "status": "success",
                "plot_path": str(plot_path),
                "url": f"/static/plots/{plot_path.name}"
            }

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except Exception as e:
            raise RuntimeError(f"Error creating plot: {e}")

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
