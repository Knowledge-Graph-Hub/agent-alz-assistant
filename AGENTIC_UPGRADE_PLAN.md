# Alzheimer's Research Assistant: Agentic Upgrade Plan

**Date**: October 4, 2025  
**Goal**: Transform the current Streamlit RAG app into a full agentic AI assistant for Alzheimer's research

## Current State

### What We Have
- **Streamlit web app** (`app_alz.py`) at alzassistant.org
- **Three PaperQA corpora**:
  - Small: 360 papers (Bateman_LLM_360)
  - Medium: 1,065 papers (alz_papers_1k_text) - **DEFAULT**
  - Large: 3,000 papers (alz_papers_3k_text)
- **Simple RAG**: User asks question → search corpus → stuff context → LLM answers
- **Stateless**: Each query is independent, no conversation memory
- **GitHub agent**: Separate system using Goose for async research in GitHub issues

### What's Missing
- ❌ No multi-step reasoning
- ❌ No external paper fetching
- ❌ No web search for recent papers
- ❌ No data analysis / visualization capabilities
- ❌ No conversation memory
- ❌ Can't "do science" with the user - just answers questions

## The Vision

Transform into a **full agentic scientific assistant** that can:
1. **Answer questions** using trusted corpus (current capability)
2. **Fetch external papers** via DOI/PMID when needed
3. **Search the web** for recent research (2024/2025 papers)
4. **Compare findings** across corpus and external sources
5. **Generate visualizations** (plots, tables)
6. **Execute multi-step research workflows** autonomously
7. **Maintain conversation context** for iterative exploration
8. **Query knowledge graph** (future: KGX TSV data)

### Example Agentic Workflow

**User**: "What's the latest on blood biomarkers for early AD detection? Compare with what's in our corpus."

**Agent's autonomous steps**:
1. Query PaperQA medium corpus for "blood biomarkers early Alzheimer"
2. Synthesize findings from 15 corpus papers
3. Web search for "blood biomarkers Alzheimer 2024 2025"
4. Fetch top 3 recent papers via ARTL MCP
5. Compare corpus findings (2023 and earlier) vs. recent findings
6. Generate summary with citations from both sources

**Current system**: Only does step 1  
**Agentic system**: Does all 6 steps autonomously

## Architecture Decision

### Selected Stack: NiceGUI + CBORG + OpenAI SDK

**Frontend**: NiceGUI (FastAPI-based Python UI framework)  
**Backend**: Built into NiceGUI (FastAPI)  
**LLM Orchestrator**: CBORG API (Claude via AWS Bedrock)  
**API SDK**: OpenAI SDK (CBORG is OpenAI-compatible)

```
┌─────────────────────────────────┐
│   NiceGUI Frontend              │
│   - Real-time chat interface    │
│   - Async status updates        │
│   - Material Design UI          │
│   - WebSocket communication     │
└────────────┬────────────────────┘
             │ (Integrated - same process)
             ▼
┌─────────────────────────────────┐
│   FastAPI Backend (built-in)    │
│   - Session management          │
│   - Agentic orchestration       │
│   - Tool execution              │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│   CBORG API (LBL Proxy)         │
│   - Claude via AWS Bedrock      │
│   - OpenAI-compatible format    │
│   - Model: anthropic/claude:latest
└────────────┬────────────────────┘
             │
      ┌──────┴─────┬──────────┬──────────┬──────────┐
      ▼            ▼          ▼          ▼          ▼
 ┌─────────┐  ┌────────┐ ┌─────────┐ ┌──────┐ ┌────────┐
 │ PaperQA │  │  ARTL  │ │   Web   │ │  KG  │ │ Python │
 │  Tool   │  │  Tool  │ │ Search  │ │ Tool │ │  Exec  │
 └─────────┘  └────────┘ └─────────┘ └──────┘ └────────┘
      │
      ▼
 ┌──────────────────────────────┐
 │  3 PaperQA Indexed Corpora   │
 │  ~/.pqa/indexes/...          │
 └──────────────────────────────┘
```

### Why NiceGUI?

**✅ FastAPI-based**: Backend is FastAPI (can add API endpoints easily)  
**✅ Real-time updates**: WebSocket support built-in for streaming  
**✅ Better UX**: Real-time status as agent works (30-60 second tasks)  
**✅ Async-first**: Perfect for agentic workflows  
**✅ Material Design**: Professional, modern UI out of the box  
**✅ Python-only**: No JavaScript/React knowledge needed  
**✅ Simpler than Reflex**: Less learning curve, more straightforward

**Prototype working**: `/tmp/nicegui_prototype/` - test at http://localhost:8081

### Why CBORG?

**✅ Validated**: CBORG supports function calling (tested successfully)  
**✅ Billing**: Through LBL, not personal credit card  
**✅ Budget control**: Built-in quotas and monitoring  
**✅ Simple**: OpenAI SDK is well-documented and familiar  
**✅ Already have it**: Using CBORG key at `~/cborg_alz.key`

**Trade-offs**:
- ❌ No extended thinking (Claude's advanced reasoning mode)
- ❌ No prompt caching (cost optimization)
- ✅ But: Good enough for agentic workflows, free billing

### Alternative Considered: Native Anthropic API

Would provide:
- Extended thinking for complex reasoning
- Prompt caching (reduce costs)
- Latest Claude features immediately

But requires:
- Personal billing / credit card
- More complex to manage budgets
- Not necessary for Phase 1

## Phase 1: Core Agentic Upgrade

### 1. Backend: FastAPI + Claude Orchestrator

**File**: `backend/agent.py`

```python
import openai
import os

class CBORGAlzheimerAgent:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.environ.get('CBORG_API_KEY'),
            base_url="https://api.cborg.lbl.gov"
        )
        self.model = "anthropic/claude:latest"
        self.system_prompt = self._load_from_goosehints()
    
    async def run(self, user_query: str, conversation_history: list = None):
        """Run full agentic research session"""
        messages = conversation_history or []
        messages.append({"role": "user", "content": user_query})
        
        status_updates = []
        max_iterations = 10  # Prevent infinite loops
        
        for iteration in range(max_iterations):
            # Claude decides what to do
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.get_tools(),  # PaperQA, ARTL, web, etc.
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            if not message.tool_calls:
                # No more tools needed - return final answer
                return {
                    "answer": message.content,
                    "status_updates": status_updates,
                    "conversation_history": messages
                }
            
            # Execute tools Claude requested
            messages.append(message)
            for tool_call in message.tool_calls:
                status_updates.append(f"Using {tool_call.function.name}...")
                result = await self.execute_tool(tool_call)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": str(result)
                })
            
            # Loop continues - Claude will reason about results
        
        raise Exception("Max iterations reached")
```

### 2. Tools to Implement

#### Tool 1: PaperQA (Most Important)

```python
{
    "type": "function",
    "function": {
        "name": "query_papers",
        "description": "Search the curated Alzheimer's disease paper corpus (3 sizes: small=360, medium=1k, large=3k papers). Use this FIRST for any Alzheimer's research questions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query about Alzheimer's research"
                },
                "corpus": {
                    "type": "string",
                    "enum": ["small", "medium", "large"],
                    "default": "medium",
                    "description": "Which corpus to search"
                }
            },
            "required": ["query"]
        }
    }
}

# Implementation
def query_papers(query: str, corpus: str = "medium"):
    from curategpt.wrappers.paperqa import PaperQAWrapper
    corpus_map = {"small": "1", "medium": "2", "large": "3"}
    wrapper = PaperQAWrapper(corpus_id=corpus_map[corpus])
    result = wrapper.search(query)
    return result.session.answer  # PaperQA's answer with citations
```

#### Tool 2: ARTL (Fetch External Papers)

```python
{
    "type": "function",
    "function": {
        "name": "fetch_paper",
        "description": "Retrieve full text of a specific scientific paper by DOI, PMID, or PMCID. Use when user requests a specific paper or when you need papers not in the corpus.",
        "parameters": {
            "type": "object",
            "properties": {
                "identifier": {
                    "type": "string",
                    "description": "DOI, PMID, or PMCID of the paper"
                },
                "identifier_type": {
                    "type": "string",
                    "enum": ["doi", "pmid", "pmcid"],
                    "description": "Type of identifier"
                }
            },
            "required": ["identifier", "identifier_type"]
        }
    }
}

# Implementation - call ARTL MCP or use artl-mcp package
def fetch_paper(identifier: str, identifier_type: str):
    # Use artl-mcp to fetch paper text
    # Return paper content
    pass
```

#### Tool 3: Web Search (Recent Papers)

```python
{
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for recent research papers (2024-2025). Use when looking for very recent findings not in the corpus.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    }
}

# Implementation - use Tavily API or similar
def web_search(query: str):
    # Call web search API
    # Return snippets with URLs
    pass
```

#### Tool 4: Python Execution (Future)

```python
{
    "type": "function",
    "function": {
        "name": "execute_python",
        "description": "Execute Python code to create plots, analyze data, or perform calculations",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            "required": ["code"]
        }
    }
}
```

### 3. Frontend: Streamlit Updates

**Add session state for conversation memory**:

```python
# Initialize session state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'artifacts' not in st.session_state:
    st.session_state.artifacts = {}  # plots, tables, etc.

# Add mode selector
mode = st.radio("Mode", ["Quick Answer", "Deep Research"])

# Query input
query = st.text_area("Ask a question about Alzheimer's research")

if st.button("Ask"):
    if mode == "Quick Answer":
        # Simple RAG (current behavior)
        with st.spinner("Searching..."):
            response = requests.post(
                "http://localhost:8000/api/chat/quick",
                json={"query": query}
            )
        st.markdown(response.json()["answer"])
    
    elif mode == "Deep Research":
        # Full agentic mode
        status_placeholder = st.empty()
        result_placeholder = st.empty()
        
        # Call backend
        response = requests.post(
            "http://localhost:8000/api/chat/deep",
            json={
                "query": query,
                "conversation_history": st.session_state.conversation_history
            }
        )
        
        data = response.json()
        
        # Show status updates
        for update in data["status_updates"]:
            status_placeholder.write(f"🤖 {update}")
        
        # Show final answer
        result_placeholder.markdown(data["answer"])
        
        # Update conversation history
        st.session_state.conversation_history = data["conversation_history"]
```

### 4. Async Handling (30-60 Second Queries)

**Approach**: Synchronous with progress spinner (simplest)

- User submits query
- Streamlit shows spinner with status updates
- FastAPI executes agentic loop (may take 30-60 seconds)
- Returns when done

**If this becomes too slow later**:
- Option A: Server-Sent Events (real-time streaming)
- Option B: Background job queue (Redis + Celery)
- Option C: WebSocket connection

For Phase 1, synchronous is fine.

## Knowledge Graph Integration (Deferred)

**Current state**: KGX TSV files (nodes and edges) in `kg-alzheimers` repo

**Future tool**: Query KG for entities, relationships, pathways

**Use cases**:
- "What genes are associated with Alzheimer's?"
- "Show me drugs targeting APOE"
- Use KG to find relevant papers (KG → gene list → paper search)

**Implementation** (later):
- Load KGX into DuckDB or in-memory
- Create `query_kg` tool
- Give Claude instructions on constructing queries

## System Prompt (.goosehints Integration)

Reuse the excellent system prompt from `.goosehints`:

```python
# Load from kg-alzheimers/.goosehints
SYSTEM_PROMPT = """
You are a specialized AI assistant for biomedical researchers and clinicians focused on
Alzheimer's disease and related topics.

## Your Core Mission
Support Alzheimer's researchers by:
1. Retrieving and discussing scientific publications relevant to Alzheimer's disease
2. Extracting useful information from papers about mechanisms, treatments, biomarkers, etc.
3. Facilitating researcher discussions by providing evidence-based insights
4. Conducting deep research by synthesizing findings across multiple publications

## Curated Literature Repository
- Primary source: 3 curated corpora (small=360, medium=1k, large=3k papers)
- ALWAYS check these FIRST for Alzheimer's topics
- These are HIGH-QUALITY, VETTED papers
- For papers not in corpus, use fetch_paper tool
- For very recent research (2024-2025), use web_search

## Guidelines
- Always cite sources (PMC ID or PMID)
- Quote relevant passages when appropriate
- Acknowledge uncertainties and contradictions
- Distinguish between established facts and hypotheses
- Be clear about level of evidence (in vitro, animal models, clinical trials)
- Present multiple perspectives when they exist

[... rest of .goosehints content ...]
"""
```

## Development Plan

### Prototype Phase (First)

**Goal**: Validate the architecture with minimal features

1. **FastAPI backend** with single endpoint
2. **CBORG integration** (confirmed working)
3. **One tool**: PaperQA query only
4. **Simple Streamlit frontend** to test

**Deliverable**: Can ask "What is tau protein?" → Claude uses PaperQA → returns answer

### Phase 1A: Core Tools

1. Add ARTL tool (fetch external papers)
2. Add web search tool
3. Test multi-step workflows

### Phase 1B: Enhanced UX

1. Add conversation memory
2. Add status updates during research
3. Add "Deep Research" mode
4. Show artifacts (citations, paper lists)

### Phase 1C: Advanced Features

1. Python execution for plots
2. Data analysis capabilities
3. Knowledge graph queries

## Key Files & Locations

**Current App**:
- Frontend: `src/curategpt/app/app_alz.py`
- Agent: `src/curategpt/agents/chat_agent.py` (ChatAgentAlz)
- PaperQA wrapper: `src/curategpt/wrappers/paperqa/paperqawrapper.py`

**GitHub Agent**:
- Workflow: `../kg-alzheimers/.github/workflows/ai-agent.yml`
- System prompt: `../kg-alzheimers/.goosehints`
- Config: `../kg-alzheimers/.config/goose/config.yaml`

**Server** (gassh):
- App directory: `~/curategpt/`
- Startup script: `~/curategpt/STARTUP.sh`
- Corpora:
  - `~/curategpt/data/Bateman_LLM_360/`
  - `~/curategpt/data/alz_papers_1k_text/`
  - `~/curategpt/data/alz_papers_3k_text/`
- Indexes: `~/curategpt/data/*/.pqa/indexes/`

**Keys**:
- CBORG: `~/cborg_alz.key`
- OpenAI: `~/openai.key.kgalz`
- Semantic Scholar: `~/semantic_scholar.key`

## Open Questions / Decisions Needed

1. **Rate limiting**: CBORG docs say "reasonable limits" but no specifics
   - May need to implement client-side rate limiting
   - Monitor for 429 errors

2. **Session persistence**: Where to store conversation history?
   - Option A: In-memory (lost on restart)
   - Option B: Redis (persistent, scalable)
   - Option C: SQLite (simple, file-based)

3. **Error handling**: What if agent gets stuck or Claude makes mistakes?
   - Max iterations limit (10)
   - Timeout per tool call
   - Graceful degradation

4. **Multi-user**: How to handle concurrent users?
   - Session IDs
   - Rate limiting per user
   - Resource allocation

5. **GitHub integration**: Should chat app create GitHub issues?
   - "Export to GitHub" button?
   - One-way (chat → GitHub) or bidirectional?

## Success Metrics

**Phase 1 is successful if**:
1. ✅ Can answer simple questions using PaperQA (like current app)
2. ✅ Can fetch external papers via ARTL when needed
3. ✅ Can autonomously execute 2-3 step research workflows
4. ✅ Maintains conversation context across queries
5. ✅ Provides status updates during long-running tasks
6. ✅ Properly cites sources from corpus and external papers

## Next Steps

1. **Build prototype** (FastAPI + CBORG + PaperQA tool)
2. **Test locally** with CBORG key
3. **Iterate** on tool implementations
4. **Deploy** to gassh server
5. **Get user feedback** from researchers

## Notes

- **PaperQA patches applied**: concurrency=1, 2-second sleep for Semantic Scholar rate limiting (both local and on gassh)
- **Medium corpus is default**: 1,065 papers, 1,062 indexed successfully
- **Current app working**: alzassistant.org with 3 corpora available
- **CBORG tested**: Function calling confirmed working with `anthropic/claude:latest`

---

## Implementation Progress (October 7, 2025)

### What We Built

Instead of building on the existing Streamlit app, we created a **standalone copier template** approach:

**1. nicegui-app-copier** (https://github.com/Knowledge-Graph-Hub/nicegui-app-copier)
- Standalone copier template for generating NiceGUI agentic applications
- Uses **Claude Code CLI** as the agent orchestrator (not OpenAI SDK)
- Spawns `claude` process with environment variables to connect to CBORG
- Configurable via MCP servers (artl-mcp, mcp-server-fetch, custom tools)
- Includes: app.py, agent orchestrator, pyproject.toml, CLAUDE.md for system prompts
- Generates complete, runnable projects

**2. agent-alz-assistant** (https://github.com/Knowledge-Graph-Hub/agent-alz-assistant)
- First application generated from the template
- Alzheimer's research assistant with literature retrieval
- Successfully tested locally on port 8082
- Uses CBORG via environment variables
- Ready for customization with domain-specific CLAUDE.md and PaperQA integration

### Key Architecture Decisions

**Using Claude Code CLI Instead of Custom Agentic Loop:**
- Original plan: Build custom orchestrator with OpenAI SDK → CBORG API
- **Actual implementation**: Use Claude Code CLI directly via environment variables
- Benefits:
  - Don't reinvent the wheel - Claude Code already has agentic orchestration
  - Get all built-in tools (Bash, Read, Write, Edit) for free
  - MCP servers are the standard extension mechanism
  - Simpler maintenance

**CBORG Integration:**
```bash
export ANTHROPIC_AUTH_TOKEN=$(cat ~/cborg_alz.key)
export ANTHROPIC_BASE_URL=https://api.cborg.lbl.gov
export ANTHROPIC_MODEL=anthropic/claude-sonnet
claude --print --dangerously-skip-permissions --mcp-config mcp_config.json
```

**NiceGUI as Frontend:**
- FastAPI-based (built into NiceGUI)
- Async support for spawning Claude CLI subprocess
- Real-time chat interface with Material Design

### Next Steps

1. **Customize agent-alz-assistant:**
   - Port system prompt from kg-alzheimers/.goosehints to CLAUDE.md
   - Create PaperQA MCP server to query the 3k corpus
   - Add domain-specific tools

2. **Fix artl-mcp dependency issue:**
   - onnxruntime incompatibility on macOS 12 ARM64
   - Either fix upstream or make artl-mcp optional

3. **Test agentic workflows:**
   - Multi-step research queries
   - Literature retrieval + synthesis
   - Compare corpus vs. external papers

4. **Deploy to gassh:**
   - Run as service
   - Configure for alzassistant.org domain

---

**End of Plan Document**  
*This represents the strategy as of October 4, 2025. Implementation will be iterative and may evolve based on testing and user feedback.*

*Update October 7, 2025: Initial prototype completed using copier template approach and Claude Code CLI.*

### Technical Notes

**Known Issues:**
- artl-mcp has onnxruntime dependency incompatible with macOS 12 ARM64
- Port 8080 conflicts with existing service (using 8082 for now)
- Need to use `uv run python app.py` (not just `python app.py`)

**Quick Reference:**

Generate new project from template:
```bash
copier copy --trust gh:Knowledge-Graph-Hub/nicegui-app-copier my-app
```

Run agent-alz-assistant locally:
```bash
cd /Users/jtr4v/PythonProject/agent-alz-assistant
export ANTHROPIC_AUTH_TOKEN=$(cat ~/cborg_alz.key)
export ANTHROPIC_BASE_URL=https://api.cborg.lbl.gov
export ANTHROPIC_MODEL=anthropic/claude-sonnet
uv sync
uv run python app.py
# Open http://localhost:8082
```

Test Claude CLI with CBORG:
```bash
export ANTHROPIC_AUTH_TOKEN=$(cat ~/cborg_alz.key)
export ANTHROPIC_BASE_URL=https://api.cborg.lbl.gov
export ANTHROPIC_MODEL=anthropic/claude-sonnet
echo "What is 2+2?" | claude --print
```

**File Locations:**
- Template: `/Users/jtr4v/PythonProject/nicegui-app-copier/`
- App: `/Users/jtr4v/PythonProject/agent-alz-assistant/`
- CBORG key: `~/cborg_alz.key`
- Curated papers: `~/curategpt/data/alz_papers_3k_text/`

**Resources:**
- NiceGUI docs: https://nicegui.io
- Claude Code CLI: https://docs.anthropic.com/en/docs/claude-code
- MCP specification: https://modelcontextprotocol.io
- Copier docs: https://copier.readthedocs.io

### GitHub Actions Integration (Future Goal)

**Goal:** Enable ephemeral runs in GitHub Actions for one-off queries without the web interface.

The planned approach would:
- Clone the repo on-the-fly
- Install dependencies with `uv`
- Use Claude CLI directly (bypassing the web UI)
- Run a single query and exit

**Target workflow pattern:**
```yaml
name: Query Agent
on: 
  workflow_dispatch:
    inputs:
      question:
        description: 'Question to ask'
        required: true

jobs:
  ask:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: astral-sh/setup-uv@v1
      
      - name: Ask question
        env:
          ANTHROPIC_AUTH_TOKEN: ${{ secrets.CBORG_API_KEY }}
          ANTHROPIC_BASE_URL: https://api.cborg.lbl.gov
          ANTHROPIC_MODEL: anthropic/claude-sonnet
        run: |
          uv sync
          echo "${{ inputs.question }}" | uv run claude --print --dangerously-skip-permissions --mcp-config mcp_config.json
```

**Use cases:**
- Automated research queries in CI/CD pipelines
- Batch processing questions from issues
- Scheduled literature reviews
- Integration with other GitHub workflows

**Status:** Not yet implemented. Requires testing and potentially adjusting the agent configuration for headless operation.

---

## Progress Notes - October 8, 2025

### PaperQA Integration (Completed)

**What was implemented:**
- Created `agent_alz_assistant/tools/paperqa/query.py` - standalone tool to query curated papers
- Vendored PaperQA logic (removed curategpt dependency, use paper-qa directly)
- Uses absolute paths for corpora and indexes to prevent unwanted rebuilding
- Supports 3 corpora: small (360), medium (1k), large (3k)
- Added sample questions UI for user onboarding
- Agent runs from project root so CLAUDE.md is loaded
- Markdown rendering for formatted answers

**Testing:**
- ✅ Successfully queries Bateman_LLM_360 (360 papers)
- ✅ Successfully queries alz_papers_3k_text (3k papers)
- ✅ Indexes match server (same hash for large corpus)
- ✅ Returns answers with citations in seconds

**Environment variables required:**
```bash
PQA_HOME1=/absolute/path/to/Bateman_LLM_360
PQA_INDEX1=/absolute/path/to/.pqa/indexes/pqa_index_xxxxx
PQA_HOME3=/absolute/path/to/alz_papers_3k_text
PQA_INDEX3=/absolute/path/to/.pqa/indexes/pqa_index_9ff473ec92621a85e2c0ff86aa96e5d9
OPENAI_API_KEY=your-key-here
```

### Known Issues & Next Steps

**Issue 1: Citation Tracking**
- PaperQA returns citations like `(Weiner2012, Biomarker2025)` but we don't have easy access to:
  - Full paper titles
  - PMC IDs or PMIDs
  - Links to papers
  - Which corpus the citation came from
  
**Needed:** Enhance query.py to return structured citation data, not just the answer text.

**Possible solutions:**
1. Parse `result.session.contexts` from PaperQA to extract full citation metadata
2. Return JSON with `{answer: "...", citations: [{pmcid, title, excerpt, ...}]}`
3. Display citations as a separate collapsible section in UI

**Issue 2: ARTL MCP Integration**
- artl-mcp is in mcp_config.json but disabled (commented out)
- Dependency issue: onnxruntime incompatible with macOS 12 ARM64
- Need to either:
  1. Fix artl-mcp upstream dependency
  2. Make it optional/conditional
  3. Use alternative paper fetching method

**Once working, ARTL would enable:**
- Fetching papers by DOI/PMID/PMCID not in curated corpus
- Comparing curated vs. external recent papers
- Building citations with external sources

**Issue 3: Reasoning/Tool Call Visibility**
- Attempted to show Claude's tool calls and reasoning in UI
- Claude CLI with `--print` outputs final answer only, not intermediate steps
- Without `--print`, output format is hard to parse
- `--verbose` flag doesn't show what we expected

**Current behavior:** Simple "Thinking..." indicator, then final answer

**Future options:**
1. Accept this limitation (simple is fine)
2. Parse Claude CLI JSON output if available
3. Build custom agentic loop instead of using Claude CLI subprocess
4. Add logging/instrumentation to track which tools are called

### Next Priorities

1. **Improve citation tracking** - Most important for researchers
   - Return structured citation metadata from PaperQA
   - Display citations prominently with PMC IDs and links
   
2. **Fix/enable ARTL MCP** - Extends beyond curated corpus
   - Resolve onnxruntime dependency issue
   - Test external paper retrieval
   - Update CLAUDE.md with ARTL usage instructions

3. **Test that Claude actually uses PaperQA** - Validation
   - Verify CLAUDE.md instructions are followed
   - Check if agent calls the bash tool to run query.py
   - May need to adjust prompting

4. **Optional: Web search integration** - For recent 2024/2025 papers
   - Only after ARTL is working
   - Lower priority than citation tracking
