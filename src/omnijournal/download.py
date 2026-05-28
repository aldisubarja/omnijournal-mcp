"""OA-first PDF download."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import httpx

from omnijournal.config import Config
from omnijournal.models import DownloadResult
from omnijournal.providers import Provider, SearchType
from omnijournal.search import meta_search


def _sanitize_filename(identifier: str) -> str:
    return re.sub(r"[^\w\-.]", "_", identifier) + ".pdf"


async def _download_pdf(client: httpx.AsyncClient, url: str, dest: Path) -> bool:
    try:
        resp = await client.get(
            url,
            follow_redirects=True,
            timeout=60.0,
            headers={"User-Agent": "omnijournal/0.1", "Accept": "application/pdf,*/*"},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and resp.content[:5] != b"%PDF-":
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return True
    except Exception:
        return False


async def download_pdf_by_identifier(
    identifier: str,
    providers: list[Provider],
    client: httpx.AsyncClient,
    config: Config,
    directory: str | None = None,
) -> DownloadResult:
    dest_dir = Path(directory).expanduser() if directory else config.download_dir
    dest = dest_dir / _sanitize_filename(identifier)
    if dest.exists():
        return DownloadResult(identifier=identifier, success=True, file_path=str(dest), source="cache")

    result = await meta_search(identifier, providers, config, limit=5)
    oa_candidates = [p for p in result.papers if p.pdf_url]

    for paper in oa_candidates:
        if paper.pdf_url and await _download_pdf(client, paper.pdf_url, dest):
            return DownloadResult(identifier=identifier, success=True, file_path=str(dest), source=paper.source)

    # Direct provider lookup fallback
    for provider in sorted(providers, key=lambda p: p.priority, reverse=True):
        try:
            pdf_url = await asyncio.wait_for(provider.get_pdf_url(identifier), timeout=config.provider_timeout)
            if pdf_url and await _download_pdf(client, pdf_url, dest):
                return DownloadResult(identifier=identifier, success=True, file_path=str(dest), source=provider.name)
        except Exception:
            continue

    return DownloadResult(identifier=identifier, success=False, error="No OA PDF found across providers.")
