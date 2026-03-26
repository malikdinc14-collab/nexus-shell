# Idea: Workspace Embedding & Indexing

## Problem Statement
Code search in nexus-shell is limited to literal text matching (grep/ripgrep). There's no semantic understanding of the codebase. Claude Code starts each session without awareness of which files are most relevant to the task.

## Proposed Solution
On workspace attach, index the codebase into embeddings via model-server. Store vectors locally in `.nexus/index/`. Enable semantic search, context injection for Claude Code, and AI-powered completions.

## Key Features
- **Auto-indexing**: On workspace attach, walk project files, chunk, embed via model-server's `/v1/embeddings` endpoint.
- **Semantic search**: `nexus search "where does auth happen"` returns ranked files by embedding similarity.
- **Context injection**: Before Claude starts, feed most relevant files based on prompt embedding similarity.
- **Incremental reindexing**: `claude.file_edit` connector triggers re-embedding of changed files only.
- **Cross-project search**: Multi-folder workspaces search across all indexed roots.
- **Local-only**: All vectors stored locally in `.nexus/index/vectors.db`. No external API.

## Architecture
```
project attach
    │
    ├─► boot.yaml creates embedding slot
    │       POST /v1/slots {"model_id": "nomic-embed", "backend": "mlx"}
    │
    ├─► core/engine/index/embedder.py chunks + embeds files
    │       POST model-server /v1/embeddings (batched)
    │
    ├─► core/engine/index/store.py saves to .nexus/index/vectors.db
    │
    └─► core/engine/index/searcher.py queries on demand

claude.file_edit event
    │
    └─► connector triggers re-embed of changed file (incremental)
```

## Dependencies
- model-server running with an embedding model loaded
- `.nexus/` project config (Phase 4A)

## Target User
Developers who want semantic code understanding and AI-enhanced search within their workspace.
