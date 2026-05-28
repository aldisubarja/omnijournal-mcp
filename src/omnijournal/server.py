"""FastMCP server exposing omnijournal tools."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastmcp import FastMCP

from omnijournal.bibliography import generate_bibliography
from omnijournal.config import Config
from omnijournal.download import download_pdf_by_identifier
from omnijournal.models import SourceStatus
from omnijournal.providers import SearchType, create_all_providers
from omnijournal.search import detect_search_type, meta_search

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

config = Config()
config.ensure_dirs()
client: httpx.AsyncClient | None = None
providers = []


@asynccontextmanager
async def lifespan(_: FastMCP) -> AsyncIterator[None]:
    global client, providers
    client = httpx.AsyncClient(timeout=config.provider_timeout, follow_redirects=True)
    providers = create_all_providers(client, config)
    try:
        yield
    finally:
        if client is not None:
            await client.aclose()


mcp = FastMCP("omnijournal", lifespan=lifespan)


def _provider(name: str):
    for p in providers:
        if p.name == name:
            return p
    return None


@mcp.tool()
async def search_papers(
    query: str,
    limit: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    sources: list[str] | None = None,
    open_access_only: bool = False,
) -> dict:
    """Search academic papers across multiple sources."""
    result = await meta_search(query, providers, config, limit=limit, source_names=sources)
    papers = result.papers
    if year_from is not None:
        papers = [p for p in papers if p.year is None or p.year >= year_from]
    if year_to is not None:
        papers = [p for p in papers if p.year is None or p.year <= year_to]
    if open_access_only:
        papers = [p for p in papers if p.is_open_access or p.pdf_url]
    return {
        "query": query,
        "search_type": result.search_type,
        "providers_searched": result.providers_searched,
        "providers_failed": result.providers_failed,
        "results": [p.model_dump() for p in papers[:limit]],
        "total_results": len(papers[:limit]),
    }


@mcp.tool()
async def search_by_author(author_name: str, limit: int = 10, sources: list[str] | None = None) -> dict:
    """Search papers by author name."""
    result = await meta_search(author_name, providers, config, search_type=SearchType.AUTHOR, limit=limit, source_names=sources)
    return result.model_dump()


@mcp.tool()
async def get_paper(identifier: str) -> dict:
    """Resolve a single paper by DOI/arXiv/PMID or direct identifier-like query."""
    result = await meta_search(identifier, providers, config, limit=1)
    return {"result": result.papers[0].model_dump() if result.papers else None}


@mcp.tool()
async def resolve_identifier(identifier: str, target_format: str = "best") -> dict:
    """Resolve a paper identifier to known canonical IDs."""
    result = await meta_search(identifier, providers, config, limit=1)
    if not result.papers:
        return {"result": None}
    paper = result.papers[0]
    return {
        "doi": paper.doi,
        "arxiv_id": paper.arxiv_id,
        "pmid": paper.pmid,
        "openalex_id": paper.openalex_id,
        "semantic_scholar_id": paper.semantic_scholar_id,
        "target_format": target_format,
    }


async def _s2_graph(identifier: str, edge: str, limit: int) -> dict:
    paper = (await meta_search(identifier, providers, config, limit=1)).papers
    if not paper:
        return {"results": [], "source": "semantic_scholar", "warning": "paper not found"}
    p = paper[0]
    paper_id = p.semantic_scholar_id or (f"DOI:{p.doi}" if p.doi else None) or (f"ArXiv:{p.arxiv_id}" if p.arxiv_id else None)
    if not paper_id:
        return {"results": [], "source": "semantic_scholar", "warning": "semantic scholar id unavailable"}
    ss = _provider("semantic_scholar")
    headers = ss._headers() if ss else {}
    resp = await client.get(
        f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/{edge}",
        params={"limit": limit, "fields": "title,authors,year,venue,abstract,externalIds,citationCount,url,openAccessPdf,isOpenAccess"},
        headers=headers,
    )
    resp.raise_for_status()
    payload = resp.json().get("data", [])
    results = []
    for item in payload:
        paper_item = item.get("citingPaper") or item.get("citedPaper") or item
        parsed = _provider("semantic_scholar")._parse(paper_item) if _provider("semantic_scholar") else None
        if parsed:
            results.append(parsed.model_dump())
    return {"results": results, "source": "semantic_scholar"}


@mcp.tool()
async def get_citations(paper_id: str, limit: int = 10) -> dict:
    """Get papers that cite a given paper."""
    return await _s2_graph(paper_id, "citations", limit)


@mcp.tool()
async def get_references(paper_id: str, limit: int = 10) -> dict:
    """Get papers referenced by a given paper."""
    return await _s2_graph(paper_id, "references", limit)


@mcp.tool()
async def get_related_papers(paper_id: str, limit: int = 10) -> dict:
    """Get related/recommended papers via Semantic Scholar recommendations."""
    result = await meta_search(paper_id, providers, config, limit=1)
    if not result.papers:
        return {"results": [], "warning": "paper not found"}
    p = result.papers[0]
    paper_id = p.semantic_scholar_id or (f"DOI:{p.doi}" if p.doi else None)
    if not paper_id:
        return {"results": [], "warning": "semantic scholar id unavailable"}
    ss = _provider("semantic_scholar")
    headers = ss._headers() if ss else {}
    resp = await client.get(
        f"https://api.semanticscholar.org/recommendations/v1/papers/forpaper/{paper_id}",
        params={"limit": limit, "fields": "title,authors,year,venue,abstract,externalIds,citationCount,url,openAccessPdf,isOpenAccess"},
        headers=headers,
    )
    resp.raise_for_status()
    payload = resp.json().get("recommendedPapers", [])
    out = []
    for item in payload:
        parsed = _provider("semantic_scholar")._parse(item) if _provider("semantic_scholar") else None
        if parsed:
            out.append(parsed.model_dump())
    return {"results": out, "source": "semantic_scholar"}


@mcp.tool()
async def download_pdf(identifier: str, directory: str | None = None) -> dict:
    """Download an OA PDF for the given DOI/arXiv/PMID if available."""
    result = await download_pdf_by_identifier(identifier, providers, client, config, directory)
    return result.model_dump()


@mcp.tool()
async def generate_bibliography_tool(identifiers: list[str], format: str = "bibtex") -> dict:
    """Generate bibliography entries from paper identifiers."""
    return await generate_bibliography(identifiers, providers, config, format)


@mcp.tool()
def healthcheck() -> dict:
    """Return source and config status."""
    return {
        "status": "ok",
        "data_dir": str(config.data_dir),
        "cache_dir": str(config.cache_dir),
        "download_dir": str(config.download_dir),
        "openalex_email_configured": bool(config.openalex_email),
        "crossref_email_configured": bool(config.crossref_email),
        "semantic_scholar_api_key_configured": bool(config.semantic_scholar_api_key),
        "unpaywall_email_configured": bool(config.unpaywall_email),
        "providers": [
            SourceStatus(
                name=p.name,
                enabled=True,
                priority=p.priority,
                supports_pdf_lookup=p.supports_pdf_lookup,
            ).model_dump()
            for p in providers
        ],
    }


@mcp.tool()
def list_sources() -> dict:
    """List enabled source providers and their capabilities."""
    return {
        "sources": [
            SourceStatus(
                name=p.name,
                enabled=True,
                priority=p.priority,
                supports_pdf_lookup=p.supports_pdf_lookup,
            ).model_dump()
            for p in providers
        ]
    }


def main() -> None:
    mcp.run(transport="stdio", show_banner=False)
