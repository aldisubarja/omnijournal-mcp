# omnijournal-mcp

Unified academic research MCP server.

## Features
- Parallel meta-search across OpenAlex, Crossref, Semantic Scholar, arXiv, Europe PMC, and DBLP
- Unified normalized paper schema
- DOI/author/keyword search detection
- Related papers, citations, references
- OA-first PDF download
- Bibliography generation

## Install
```bash
cd ~/projects/omnijournal-mcp
source .venv/bin/activate
pip install -e .
```

## Run
```bash
omnijournal-mcp
```

## Environment
Optional:
- `OPENALEX_EMAIL`
- `CROSSREF_EMAIL`
- `SEMANTIC_SCHOLAR_API_KEY`
- `UNPAYWALL_EMAIL`
- `OMNIJOURNAL_DATA_DIR`
