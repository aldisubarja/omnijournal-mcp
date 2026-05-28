"""Simple bibliography generation from normalized Paper data."""

from __future__ import annotations

from omnijournal.config import Config
from omnijournal.providers import Provider, SearchType
from omnijournal.search import meta_search


def _bibtex_key(title: str, year: int | None, first_author: str | None) -> str:
    surname = (first_author or "unknown").split()[-1].lower()
    stem = "".join(ch for ch in title.lower() if ch.isalnum())[:12]
    return f"{surname}{year or 'nd'}{stem}"


def _format_authors(authors: list[str], style: str = "and") -> str:
    if style == "and":
        return " and ".join(authors)
    if style == "comma":
        return ", ".join(authors)
    return "; ".join(authors)


async def generate_bibliography(
    identifiers: list[str],
    providers: list[Provider],
    config: Config,
    format: str = "bibtex",
) -> dict:
    entries: list[str] = []
    fmt = format.lower()

    for identifier in identifiers:
        result = await meta_search(
            identifier,
            providers,
            config,
            search_type=SearchType.DOI,
            limit=1,
        )
        if not result.papers:
            entries.append(f"[not found] {identifier}")
            continue
        paper = result.papers[0]
        author_names = [a.name for a in paper.authors]
        if fmt == "bibtex":
            key = _bibtex_key(paper.title, paper.year, author_names[0] if author_names else None)
            entry = (
                f"@article{{{key},\n"
                f"  title = {{{paper.title}}},\n"
                f"  author = {{{_format_authors(author_names, 'and')}}},\n"
                f"  year = {{{paper.year or ''}}},\n"
                f"  journal = {{{paper.journal or paper.venue or ''}}},\n"
                f"  doi = {{{paper.doi or ''}}},\n"
                f"  url = {{{paper.url or ''}}}\n"
                f"}}"
            )
        elif fmt == "apa":
            entry = f"{_format_authors(author_names, 'comma')} ({paper.year or 'n.d.'}). {paper.title}. {paper.journal or paper.venue or ''}. {paper.doi or paper.url or ''}"
        elif fmt == "mla":
            entry = f"{_format_authors(author_names, 'comma')}. \"{paper.title}.\" {paper.journal or paper.venue or ''}, {paper.year or ''}, {paper.doi or paper.url or ''}."
        elif fmt == "chicago":
            entry = f"{_format_authors(author_names, 'comma')}. {paper.year or 'n.d.'}. \"{paper.title}.\" {paper.journal or paper.venue or ''}. {paper.doi or paper.url or ''}."
        else:
            entry = f"{paper.title} — {paper.doi or paper.url or ''}"
        entries.append(entry)

    return {"format": fmt, "entries": entries}
