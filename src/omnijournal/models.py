"""Unified data models for omnijournal-mcp."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Author(BaseModel):
    name: str
    affiliation: str | None = None
    orcid: str | None = None


class Paper(BaseModel):
    title: str
    authors: list[Author] = Field(default_factory=list)
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    pmid: str | None = None
    openalex_id: str | None = None
    semantic_scholar_id: str | None = None
    year: int | None = None
    venue: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    citation_count: int | None = None
    is_open_access: bool = False
    source_priority: int = 0
    sources_seen: list[str] = Field(default_factory=list)
    source: str = ""

    @field_validator("doi")
    @classmethod
    def normalize_doi(cls, v: str | None) -> str | None:
        if not v:
            return v
        value = v.strip()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if value.lower().startswith(prefix.lower()):
                value = value[len(prefix):]
        return value

    def merge_from(self, other: "Paper") -> "Paper":
        """Merge another paper into this one, keeping best available fields.

        The higher-priority source wins when both contain conflicting non-empty data.
        """
        take_other = other.source_priority > self.source_priority

        def choose(a, b):
            if a in (None, "", [], False):
                return b
            if b in (None, "", [], False):
                return a
            return b if take_other else a

        merged = Paper(
            title=choose(self.title, other.title),
            authors=choose(self.authors, other.authors),
            abstract=choose(self.abstract, other.abstract),
            doi=choose(self.doi, other.doi),
            arxiv_id=choose(self.arxiv_id, other.arxiv_id),
            pmid=choose(self.pmid, other.pmid),
            openalex_id=choose(self.openalex_id, other.openalex_id),
            semantic_scholar_id=choose(self.semantic_scholar_id, other.semantic_scholar_id),
            year=choose(self.year, other.year),
            venue=choose(self.venue, other.venue),
            url=choose(self.url, other.url),
            pdf_url=choose(self.pdf_url, other.pdf_url),
            journal=choose(self.journal, other.journal),
            volume=choose(self.volume, other.volume),
            issue=choose(self.issue, other.issue),
            pages=choose(self.pages, other.pages),
            citation_count=choose(self.citation_count, other.citation_count),
            is_open_access=self.is_open_access or other.is_open_access,
            source_priority=max(self.source_priority, other.source_priority),
            sources_seen=sorted(set(self.sources_seen + other.sources_seen + [self.source, other.source])),
            source=other.source if take_other else self.source,
        )
        return merged


class SearchResult(BaseModel):
    query: str
    search_type: str
    papers: list[Paper] = Field(default_factory=list)
    total_results: int = 0
    providers_searched: list[str] = Field(default_factory=list)
    providers_failed: list[str] = Field(default_factory=list)


class DownloadResult(BaseModel):
    identifier: str
    success: bool
    file_path: str | None = None
    error: str | None = None
    source: str | None = None


class BibliographyResult(BaseModel):
    format: str
    entries: list[str] = Field(default_factory=list)


class SourceStatus(BaseModel):
    name: str
    enabled: bool = True
    priority: int = 0
    supports_pdf_lookup: bool = False
    notes: str | None = None
