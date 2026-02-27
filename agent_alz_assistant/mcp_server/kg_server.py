#!/usr/bin/env python
"""MCP server for querying the kg-alzheimers knowledge graph via DuckDB.

Loads KGX-format TSV files (nodes + edges) into a persistent on-disk DuckDB
database and exposes search/query tools over the Model Context Protocol.

On first run the TSV files are imported and indexed; subsequent starts reuse
the on-disk database file, keeping memory usage low.
"""

import asyncio
import json
import os
from pathlib import Path

import duckdb
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

app = Server("kg-server")

# Module-level DuckDB connection, initialised at startup.
_db: duckdb.DuckDBPyConnection | None = None


def _get_db() -> duckdb.DuckDBPyConnection:
    if _db is None:
        raise RuntimeError("DuckDB not initialised – call _init_db() first")
    return _db


def _init_db() -> duckdb.DuckDBPyConnection:
    """Open (or create) a persistent on-disk DuckDB database.

    If the database file already exists the TSV import is skipped entirely,
    making subsequent starts near-instant and keeping RAM usage low.
    """
    global _db

    data_dir = os.environ.get("KG_DATA_DIR")
    if not data_dir:
        raise ValueError("KG_DATA_DIR environment variable is not set!")

    data_path = Path(data_dir).expanduser().resolve()
    db_file = data_path / "kg-alzheimers.duckdb"
    nodes_file = data_path / "kg-alzheimers_nodes.tsv"
    edges_file = data_path / "kg-alzheimers_edges.tsv"

    needs_import = not db_file.exists()

    if needs_import:
        for f in (nodes_file, edges_file):
            if not f.exists():
                raise FileNotFoundError(f"KGX file not found: {f}")

    conn = duckdb.connect(str(db_file))

    if needs_import:
        print("[KG] Importing TSV files into DuckDB (first run, this may take a few minutes)...")

        # Load nodes — keep the columns we actually need.
        conn.execute(f"""
            CREATE TABLE nodes AS
            SELECT
                id,
                category,
                name,
                description,
                synonym,
                exact_synonyms,
                symbol,
                full_name,
                in_taxon_label
            FROM read_csv('{nodes_file}',
                          delim='\t', header=true, quote='',
                          ignore_errors=true, all_varchar=true)
        """)

        # Load edges — keep useful columns.
        conn.execute(f"""
            CREATE TABLE edges AS
            SELECT
                subject,
                predicate,
                object,
                category,
                primary_knowledge_source,
                publications,
                knowledge_level,
                has_evidence,
                negated
            FROM read_csv('{edges_file}',
                          delim='\t', header=true, quote='',
                          ignore_errors=true, all_varchar=true)
        """)

        # Indexes for fast lookups.
        conn.execute("CREATE INDEX idx_nodes_id ON nodes(id)")
        conn.execute("CREATE INDEX idx_edges_subject ON edges(subject)")
        conn.execute("CREATE INDEX idx_edges_object ON edges(object)")

        node_count = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        edge_count = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        print(f"[KG] Import complete: {node_count:,} nodes, {edge_count:,} edges")
    else:
        print(f"[KG] Using existing database: {db_file}")

    _db = conn
    return conn


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def search_kg_nodes(query: str, category: str | None = None, limit: int = 20) -> list[dict]:
    """Search nodes by name / synonym with optional category filter."""
    db = _get_db()
    pattern = f"%{query}%"

    where = "WHERE (name ILIKE ? OR synonym ILIKE ? OR exact_synonyms ILIKE ? OR symbol ILIKE ?)"
    params: list = [pattern, pattern, pattern, pattern]

    if category:
        where += " AND category ILIKE ?"
        params.append(f"%{category}%")

    sql = f"""
        SELECT id, category, name, symbol, description
        FROM nodes
        {where}
        LIMIT ?
    """
    params.append(limit)

    rows = db.execute(sql, params).fetchall()
    cols = ["id", "category", "name", "symbol", "description"]
    return [dict(zip(cols, row)) for row in rows]


def query_kg_edges(
    subject: str | None = None,
    object_: str | None = None,
    predicate: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Find edges by subject / object / predicate, joined to node names."""
    db = _get_db()

    conditions = []
    params: list = []

    if subject:
        conditions.append("e.subject = ?")
        params.append(subject)
    if object_:
        conditions.append("e.object = ?")
        params.append(object_)
    if predicate:
        conditions.append("e.predicate ILIKE ?")
        params.append(f"%{predicate}%")

    if not conditions:
        raise ValueError("At least one of subject, object, or predicate is required")

    where = " AND ".join(conditions)

    sql = f"""
        SELECT
            s.name  AS subject_name,
            e.subject AS subject_id,
            e.predicate,
            o.name  AS object_name,
            e.object AS object_id,
            e.primary_knowledge_source,
            e.publications
        FROM edges e
        LEFT JOIN nodes s ON e.subject = s.id
        LEFT JOIN nodes o ON e.object  = o.id
        WHERE {where}
        LIMIT ?
    """
    params.append(limit)

    rows = db.execute(sql, params).fetchall()
    cols = [
        "subject_name", "subject_id", "predicate",
        "object_name", "object_id",
        "primary_knowledge_source", "publications",
    ]
    return [dict(zip(cols, row)) for row in rows]


def get_node_details(node_id: str) -> dict | None:
    """Get full details for a single node."""
    db = _get_db()
    row = db.execute("SELECT * FROM nodes WHERE id = ?", [node_id]).fetchone()
    if row is None:
        return None
    cols = [desc[0] for desc in db.execute("SELECT * FROM nodes LIMIT 0").description]
    return dict(zip(cols, row))


def get_node_neighbors(
    node_id: str, predicate: str | None = None, limit: int = 50
) -> list[dict]:
    """Get edges and neighbor nodes for a given node."""
    db = _get_db()

    pred_filter = ""
    params: list = [node_id, node_id]

    if predicate:
        pred_filter = "AND e.predicate ILIKE ?"
        params.append(f"%{predicate}%")

    params.append(limit)

    sql = f"""
        SELECT
            e.subject,
            s.name AS subject_name,
            e.predicate,
            e.object,
            o.name AS object_name,
            e.primary_knowledge_source,
            e.publications
        FROM edges e
        LEFT JOIN nodes s ON e.subject = s.id
        LEFT JOIN nodes o ON e.object  = o.id
        WHERE (e.subject = ? OR e.object = ?)
        {pred_filter}
        LIMIT ?
    """

    rows = db.execute(sql, params).fetchall()
    cols = [
        "subject_id", "subject_name", "predicate",
        "object_id", "object_name",
        "primary_knowledge_source", "publications",
    ]
    return [dict(zip(cols, row)) for row in rows]


# ---------------------------------------------------------------------------
# MCP handlers
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_kg_nodes",
            description=(
                "Search the Alzheimer's knowledge graph for nodes (genes, diseases, drugs, "
                "pathways, etc.) by name or synonym. Returns matching node IDs, categories, "
                "names, and descriptions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term (gene name, disease, drug, etc.)",
                    },
                    "category": {
                        "type": "string",
                        "description": (
                            "Optional biolink category filter, e.g. 'biolink:Gene', "
                            "'biolink:Disease', 'biolink:Drug'"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 20)",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="query_kg_edges",
            description=(
                "Query edges (relationships) in the Alzheimer's knowledge graph. "
                "Filter by subject node ID, object node ID, and/or predicate. "
                "Returns subject name, predicate, object name, and publications."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Subject node ID (e.g. 'HGNC:613')",
                    },
                    "object": {
                        "type": "string",
                        "description": "Object node ID (e.g. 'MONDO:0004975')",
                    },
                    "predicate": {
                        "type": "string",
                        "description": (
                            "Predicate filter (e.g. 'biolink:gene_associated_with_condition')"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 50)",
                        "default": 50,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_node_details",
            description=(
                "Get full details for a specific node in the knowledge graph by its ID. "
                "Returns all metadata including synonyms, description, taxon, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "The node ID (e.g. 'HGNC:613', 'MONDO:0004975')",
                    },
                },
                "required": ["node_id"],
            },
        ),
        Tool(
            name="get_node_neighbors",
            description=(
                "Get all edges and neighbor nodes for a given node ID. "
                "Useful for exploring what a gene/disease/drug is connected to. "
                "Optional predicate filter to narrow relationship types."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "The node ID to find neighbors for",
                    },
                    "predicate": {
                        "type": "string",
                        "description": "Optional predicate filter (e.g. 'biolink:treats')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 50)",
                        "default": 50,
                    },
                },
                "required": ["node_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "search_kg_nodes":
            query = arguments.get("query")
            if not query:
                raise ValueError("query parameter is required")
            result = search_kg_nodes(
                query=query,
                category=arguments.get("category"),
                limit=arguments.get("limit", 20),
            )

        elif name == "query_kg_edges":
            result = query_kg_edges(
                subject=arguments.get("subject"),
                object_=arguments.get("object"),
                predicate=arguments.get("predicate"),
                limit=arguments.get("limit", 50),
            )

        elif name == "get_node_details":
            node_id = arguments.get("node_id")
            if not node_id:
                raise ValueError("node_id parameter is required")
            result = get_node_details(node_id)
            if result is None:
                result = {"error": f"Node not found: {node_id}"}

        elif name == "get_node_neighbors":
            node_id = arguments.get("node_id")
            if not node_id:
                raise ValueError("node_id parameter is required")
            result = get_node_neighbors(
                node_id=node_id,
                predicate=arguments.get("predicate"),
                limit=arguments.get("limit", 50),
            )

        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        raise RuntimeError(f"Error in {name}: {e}") from e


async def main():
    """Initialise DuckDB and run the MCP server."""
    _init_db()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
