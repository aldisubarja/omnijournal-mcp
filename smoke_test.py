"""Smoke test — hits real APIs. Fails only on 5xx / parse errors, not empty results."""
import asyncio
import sys
import httpx
from omnijournal.config import Config
from omnijournal.search import detect_search_type, meta_search
from omnijournal.providers import create_all_providers, SearchType

QUERIES = [
    ("openalex", "transformer attention", SearchType.KEYWORDS),
    ("crossref", "transformer attention", SearchType.KEYWORDS),
    ("semantic_scholar", "transformer attention", SearchType.KEYWORDS),
    ("arxiv", "transformer attention", SearchType.KEYWORDS),
    ("europe_pmc", "cancer immunotherapy", SearchType.KEYWORDS),
    ("dblp", "transformer", SearchType.KEYWORDS),
    ("pubmed", "cancer", SearchType.KEYWORDS),
    ("openreview", "transformer", SearchType.KEYWORDS),
    ("biorxiv", "genomics", SearchType.KEYWORDS),
    ("core", "transformer", SearchType.KEYWORDS),
]


async def smoke():
    config = Config()
    async with httpx.AsyncClient(timeout=config.provider_timeout, follow_redirects=True) as client:
        all_provs = create_all_providers(client, config)
        prov_map = {p.name: p for p in all_provs}
        passed, failed = 0, 0
        for name, query, stype in QUERIES:
            p = prov_map.get(name)
            if not p:
                print(f"SKIP {name} — not found")
                continue
            try:
                papers = await p.search(query, stype, limit=3)
                print(f"OK   {name}: {len(papers)} papers")
                passed += 1
            except Exception as e:
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    sys.exit(asyncio.run(smoke()))
