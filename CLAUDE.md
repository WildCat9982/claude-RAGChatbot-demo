# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

Requires Python 3.13+ and `uv`. On Windows, use Git Bash.

Always use `uv` to run the server and manage packages — never use `pip` directly.

```bash
# Install dependencies
uv sync

# Start the server (from project root)
./run.sh

# Or manually
cd backend && uv run uvicorn app:app --reload --port 8000
```

App runs at `http://localhost:8000`. The `.env` file at the project root must contain `ANTHROPIC_API_KEY`.

## Architecture

This is a full-stack RAG chatbot. The **frontend** is vanilla HTML/JS served as static files by FastAPI. All business logic lives in the **backend** Python package.

### Request lifecycle

1. Frontend POSTs `{ query, session_id }` to `POST /api/query`
2. `app.py` delegates to `RAGSystem.query()`
3. `RAGSystem` fetches conversation history from `SessionManager`, then calls `AIGenerator`
4. `AIGenerator` makes a **first Claude API call** with the `search_course_content` tool available
5. If Claude decides to search, `ToolManager` executes `CourseSearchTool` → `VectorStore.search()` → ChromaDB
6. Results are fed back in a **second Claude API call** (no tools) to synthesize the final answer
7. Sources and answer are returned to the frontend

### Key design decisions

- **Two ChromaDB collections**: `course_catalog` (course-level metadata for fuzzy name resolution) and `course_content` (text chunks for semantic search). Filtering by course/lesson is done via ChromaDB `where` clauses.
- **Tool-based retrieval**: Claude decides whether to call the search tool rather than always retrieving context. General knowledge questions bypass the vector store entirely.
- **Session history** is stored in-memory in `SessionManager` (not persisted). Capped at `MAX_HISTORY * 2` messages (default: 4).
- **Deduplication on load**: Startup skips courses already present in ChromaDB by comparing titles.

### Configuration (`backend/config.py`)

All tuneable parameters are in the `Config` dataclass — chunk size, overlap, max results, history length, model name, ChromaDB path. No changes needed elsewhere.

### Document format

Course documents in `docs/` must follow this structure for correct parsing:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<lesson content...>

Lesson 1: <title>
...
```
