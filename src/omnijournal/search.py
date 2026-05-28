"""Query detection, deduplication, merging, and parallel meta-search."""

from __future__ import annotations

import asyncio
import logging
import re

from omnijournal.config import Config
from omnijournal.models import Paper, SearchResult
from omnijournal.providers import Provider, SearchType

logger = logging.getLogger(__name__)

DOI_RE = re.compile(r"^(?:https?://doi\.org/)?10\.\d{4,}/\S+$", re.I)
AUTHOR_RE = re.compile(r"^[A-Z][a-z]+,\s*[A-Z]", re.I)
ARXIV_RE = re.compile(r"^(?:arxiv:)?\d{4}\.\d{4,5}(?:v\d+)?$", re.I)
PMID_RE = re.compile(r"^pmid:\d+$", re.I)


def _looks_like_author_query(text: str) -> bool:
    words = [w for w in re.split(r"\s+", text.strip()) if w]
    if not (2 <= len(words) <= 4):
        return False
    cleaned = [re.sub(r"[^A-Za-z'\-.]", "", w) for w in words]
    if not all(w and any(c.isalpha() for c in w) for w in cleaned):
        return False
    stopwords = {"and", "or", "for", "with", "using", "based", "the", "of", "in", "on"}
    lowered = {w.lower() for w in cleaned}
    if lowered & stopwords:
        return False
    return all(w[0].isupper() for w in cleaned if w)


def _normalize_arxiv_id(text: str) -> str:
    text = text.strip()
    if text.lower().startswith("arxiv:"):
        return text.split(":", 1)[1]
    return text


def _is_arxiv_query(text: str) -> bool:
    return bool(ARXIV_RE.match(text.strip()))


def _is_pmid_query(text: str) -> bool:
    return bool(PMID_RE.match(text.strip()))


def _is_doi_query(text: str) -> bool:
    return bool(DOI_RE.match(text.strip()))


def detect_search_type(query: str) -> SearchType:
    text = query.strip()
    if _is_arxiv_query(text):
        return SearchType.ARXIV
    if _is_doi_query(text) or _is_pmid_query(text):
        return SearchType.DOI
    if AUTHOR_RE.match(text) or _looks_like_author_query(text):
        return SearchType.AUTHOR
    return SearchType.KEYWORDS


def _normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.lower().strip())


def _paper_key(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    if paper.arxiv_id:
        return f"arxiv:{paper.arxiv_id.lower()}"
    if paper.pmid:
        return f"pmid:{paper.pmid.lower()}"
    return f"title:{_normalize_title(paper.title)}"


def _exact_match_boost(paper: Paper, query: str) -> int:
    text = query.strip()
    if _is_doi_query(text) and paper.doi and paper.doi.lower() == text.lower().removeprefix("https://doi.org/"):
        return 100
    if _is_arxiv_query(text) and paper.arxiv_id:
        query_id = _normalize_arxiv_id(text).lower()
        paper_id = _normalize_arxiv_id(paper.arxiv_id).lower()
        if paper_id == query_id:
            return 100
        if paper_id.startswith(f"{query_id}v"):
            return 95
    if _is_pmid_query(text) and paper.pmid and paper.pmid.lower() == text.lower().split(":", 1)[-1]:
        return 100
    return 0


def _rank_score(paper: Paper, query: str = "") -> tuple:
    return (
        _exact_match_boost(paper, query),
        paper.citation_count or 0,
        paper.year or 0,
        1 if paper.is_open_access or paper.pdf_url else 0,
        paper.source_priority,
        len(paper.sources_seen),
    )


def deduplicate_and_merge(papers: list[Paper], query: str = "") -> list[Paper]:
    merged: dict[str, Paper] = {}

    for paper in papers:
        key = _paper_key(paper)
        if key in merged:
            merged[key] = merged[key].merge_from(paper)
        else:
            merged[key] = paper

    result = list(merged.values())
    result.sort(key=lambda paper: _rank_score(paper, query), reverse=True)
    return result


async def meta_search(
    query: str,
    providers: list[Provider],
    config: Config,
    search_type: SearchType | None = None,
    limit: int = 10,
    source_names: list[str] | None = None,
) -> SearchResult:
    search_type = search_type or detect_search_type(query)
    if _is_arxiv_query(query):
        applicable = [p for p in providers if SearchType.DOI in p.supported_search_types]
        preferred = {"arxiv", "semantic_scholar"}
        narrowed = [p for p in applicable if p.name in preferred]
        if narrowed:
            applicable = narrowed
    else:
        applicable = [p for p in providers if search_type in p.supported_search_types]
    if source_names:
        source_set = {name.strip().lower() for name in source_names}
        applicable = [p for p in applicable if p.name.lower() in source_set]

    if not applicable:
        return SearchResult(query=query, search_type=search_type.name, total_results=0)

    sem = asyncio.Semaphore(config.max_parallel_providers)
    all_papers: list[Paper] = []
    providers_searched: list[str] = []
    providers_failed: list[str] = []

    async def _query_provider(provider: Provider) -> None:
        async with sem:
            try:
                provider_query = query
                if provider.name == "arxiv" and _is_arxiv_query(query):
                    provider_query = f"arxiv:{_normalize_arxiv_id(query)}"
                papers = await asyncio.wait_for(
                    provider.search(provider_query, search_type, limit=limit),
                    timeout=config.provider_timeout,
                )
                all_papers.extend(papers)
                providers_searched.append(provider.name)
            except Exception as exc:
                logger.warning("Provider %s failed: %s", provider.name, exc)
                providers_failed.append(provider.name)

    await asyncio.gather(*[_query_provider(p) for p in applicable])
    deduped = deduplicate_and_merge(all_papers, query=query)[:limit]
    return SearchResult(
        query=query,
        search_type=search_type.name,
        papers=deduped,
        total_results=len(deduped),
        providers_searched=sorted(providers_searched),
        providers_failed=sorted(providers_failed),
    )
