"""PubMed provider — biomedical gold standard via E-utilities."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from omnijournal.models import Author, Paper
from omnijournal.providers import Provider, SearchType

_PMC_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedProvider(Provider):
    name = "pubmed"
    priority = 175
    base_delay = 0.34  # ~3 req/sec
    supported_search_types = [SearchType.KEYWORDS, SearchType.DOI, SearchType.AUTHOR]

    async def search(self, query: str, search_type: SearchType, limit: int = 10) -> list[Paper]:
        await self._rate_limit()
        # Search for IDs first
        params = {"db": "pubmed", "term": query, "retmax": limit, "retmode": "json", "sort": "relevance"}
        resp = await self.client.get(f"{_PMC_URL}/esearch.fcgi", params=params)
        resp.raise_for_status()
        id_list = resp.json().get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []
        # Fetch summaries
        params2 = {"db": "pubmed", "id": ",".join(id_list), "retmode": "xml"}
        resp2 = await self.client.get(f"{_PMC_URL}/efetch.fcgi", params=params2)
        resp2.raise_for_status()
        return self._parse(resp2.text, id_list)

    def _parse(self, xml_text: str, requested_ids: list[str]) -> list[Paper]:
        root = ET.fromstring(xml_text)
        requested = set(requested_ids)
        papers: list[Paper] = []
        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None else None
            if pmid not in requested:
                continue
            title_el = article.find(".//ArticleTitle")
            title = (title_el.text or "").strip() if title_el is not None else ""
            if not title:
                continue
            abstract_parts = []
            for ab in article.findall(".//AbstractText"):
                label = ab.get("Label", "")
                txt = ab.text or ""
                if label:
                    abstract_parts.append(f"{label}: {txt}")
                else:
                    abstract_parts.append(txt)
            year = None
            pub_date = article.find(".//PubDate")
            if pub_date is not None:
                yr = pub_date.find("Year")
                if yr is not None and yr.text:
                    year = int(yr.text)
            authors: list[Author] = []
            for a in article.findall(".//Author"):
                ln = a.find("LastName")
                fn = a.find("ForeName")
                name = " ".join(filter(None, [fn.text if fn is not None else None, ln.text if ln is not None else None]))
                if name:
                    authors.append(Author(name=name))
            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else None
            doi_el = article.find(".//ArticleId[@IdType='doi']")
            doi = doi_el.text if doi_el is not None else None
            papers.append(Paper(
                title=title,
                authors=authors,
                abstract="\n".join(abstract_parts) or None,
                pmid=pmid,
                doi=doi,
                year=year,
                venue=journal,
                journal=journal,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else None,
                source_priority=self.priority,
                source=self.name,
            ))
        return papers
