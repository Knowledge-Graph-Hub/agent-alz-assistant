#!/usr/bin/env python
"""Query the curated Alzheimer's papers corpus using PaperQA.

Usage:
    python -m agent_alz_assistant.tools.paperqa.query "your query here" [corpus_id]
    
Arguments:
    query: Natural language question about Alzheimer's research
    corpus_id: Optional. 1=small (360 papers), 2=medium (1k papers), 3=large (3k papers)
               Default: 2 (medium)

Example:
    python -m agent_alz_assistant.tools.paperqa.query "What is tau protein?" 2

Environment Variables Required:
    PQA_HOME1 - Path to small corpus directory
    PQA_INDEX1 - Index name for small corpus
    PQA_HOME2 - Path to medium corpus directory (default)
    PQA_INDEX2 - Index name for medium corpus (default)
    PQA_HOME3 - Path to large corpus directory
    PQA_INDEX3 - Index name for large corpus
"""

import asyncio
import os
import sys

from paperqa import Settings
from paperqa.agents.main import agent_query
from paperqa.agents.search import get_directory_index


async def query_paperqa(query: str, corpus_id: str = "2"):
    """Query PaperQA with the given corpus."""
    
    # Get environment variables - ABSOLUTE PATHS ONLY
    pqa_home_var = f"PQA_HOME{corpus_id}"
    pqa_index_var = f"PQA_INDEX{corpus_id}"
    
    pqa_home = os.environ.get(pqa_home_var)
    if not pqa_home:
        raise ValueError(f"{pqa_home_var} environment variable is not set!")
    
    pqa_index = os.environ.get(pqa_index_var)
    if not pqa_index:
        raise ValueError(f"{pqa_index_var} environment variable is not set!")
    
    # Verify paths exist
    from pathlib import Path
    home_path = Path(pqa_home).expanduser().resolve()
    index_path = Path(pqa_index).expanduser().resolve()
    
    if not home_path.exists():
        raise ValueError(f"PQA_HOME{corpus_id} does not exist: {home_path}")
    
    if not index_path.exists():
        raise ValueError(f"PQA_INDEX{corpus_id} does not exist: {index_path}")
    
    # Configure PaperQA settings with absolute paths
    settings = Settings(paper_directory=str(home_path))
    settings.agent.index.index_directory = str(index_path.parent)
    settings.agent.index.name = index_path.name
    
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
    return response


def main():
    if len(sys.argv) < 2:
        print("Error: Query required", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    corpus_id = sys.argv[2] if len(sys.argv) > 2 else "2"
    
    # Map friendly names to corpus IDs
    corpus_map = {
        "small": "1",
        "medium": "2", 
        "large": "3",
        "1": "1",
        "2": "2",
        "3": "3"
    }
    
    corpus_id = corpus_map.get(corpus_id, corpus_id)
    
    try:
        result = asyncio.run(query_paperqa(query, corpus_id))
        
        # Extract citations from contexts
        citations = []
        seen_docs = set()
        for ctx in result.session.contexts:
            if hasattr(ctx.text, 'doc'):
                doc = ctx.text.doc
                # Avoid duplicates
                if doc.docname not in seen_docs:
                    seen_docs.add(doc.docname)
                    citation_info = {
                        'key': doc.docname,
                        'doi': doc.doi if hasattr(doc, 'doi') and doc.doi else None,
                        'citation': doc.citation if hasattr(doc, 'citation') else None,
                        'score': ctx.score
                    }
                    # Try to extract PMC ID from filename if available
                    if doc.docname.startswith('PMC'):
                        citation_info['pmcid'] = doc.docname.split('_')[0]
                    citations.append(citation_info)
        
        # Output JSON with answer and citations
        import json
        output = {
            'answer': result.session.answer,
            'citations': citations
        }
        print(json.dumps(output, indent=2))
        
    except Exception as e:
        print(f"Error querying PaperQA: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
