# omnijournal-mcp

Unified academic research MCP server.

## Features
- Parallel meta-search across PubMed, OpenAlex, Crossref, Semantic Scholar, arXiv, Europe PMC, DBLP, OpenReview, bioRxiv, CORE, and Unpaywall
- Unified normalized paper schema
- DOI/author/keyword/arXiv/PMID search detection
- Related papers, citations, references
- OA-first PDF download
- Bibliography generation
- 11 providers, 12 tools

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

## Source Selection Guide

Use source/domain fit to improve ranking and relevance, not just keyword matching.

### Provider strengths by domain

- **PubMed**
  - Best for: biomedical journals, sports science, physiology, rehabilitation, biomechanics, injury, strength and conditioning
  - Typical domains: medicine, exercise science, kinesiology, physical therapy, musculoskeletal research
  - Good when: user asks about human performance, biomechanics, fatigue, recovery, shoulder/knee/spine issues, para sport
  - Weak when: computer science, pure mathematics, systems engineering

- **Europe PMC**
  - Best for: life sciences and biomedical literature, often overlapping with PubMed but useful for broader Europe PMC coverage
  - Typical domains: medicine, biology, translational research, physiology
  - Good when: biomedical query needs extra recall beyond PubMed
  - Weak when: CS/ML conference literature

- **Semantic Scholar**
  - Best for: citation graph, related papers, references, influence discovery
  - Typical domains: broad multidisciplinary coverage
  - Good when: user asks “paper yang related”, “siapa yang cite ini”, “paper penting di topik ini”
  - Weak when: exact biomedical indexing is more important than graph discovery

- **Crossref**
  - Best for: DOI resolution, metadata normalization, publisher-level lookup
  - Typical domains: broad journal coverage across disciplines
  - Good when: exact DOI known, or metadata enrichment/deduplication is needed
  - Weak when: abstract quality, relevance ranking, or citation graph is the main need

- **OpenAlex**
  - Best for: broad scholarly discovery, metadata enrichment, open-access signals
  - Typical domains: multidisciplinary journal and paper search
  - Good when: broad survey, ranking candidates, open access hints
  - Weak when: field-specific expert indexing matters more than breadth

- **arXiv**
  - Best for: preprints in computer science, math, physics, statistics, quantitative fields
  - Typical domains: AI/ML, NLP, CV, robotics, optimization, theoretical work
  - Good when: latest preprints matter
  - Weak when: clinical, medical, sport science journal literature is required

- **DBLP**
  - Best for: computer science bibliography
  - Typical domains: software engineering, databases, AI, systems, formal methods
  - Good when: user asks for CS authors, venues, or conference-heavy literature
  - Weak when: medicine, biomechanics, life sciences

- **OpenReview**
  - Best for: ML/AI conference submissions and reviews
  - Typical domains: machine learning, AI research
  - Good when: user wants cutting-edge AI/ML work before journal publication
  - Weak when: non-AI topics or journal-only research

- **bioRxiv**
  - Best for: biology and life-science preprints
  - Typical domains: molecular biology, neuroscience, genetics, physiology
  - Good when: preprint discovery in life sciences matters
  - Weak when: user wants only peer-reviewed journal papers

- **CORE**
  - Best for: open-access full-text discovery
  - Typical domains: broad multidisciplinary coverage
  - Good when: finding downloadable full text is more important than perfect metadata
  - Weak when: precision and clean metadata matter most

- **Unpaywall**
  - Best for: OA PDF lookup from DOI
  - Typical domains: all DOI-based scholarly literature
  - Good when: a paper is already known and the task is “find PDF/full text”
  - Weak when: discovery/search is the main task

### Recommended source priority by use case

- **Sports science / biomechanics / rehab / physiology**
  - Start with: `PubMed`, `Europe PMC`, `Semantic Scholar`
  - Enrich with: `Crossref`, `OpenAlex`

- **Medicine / clinical / human performance**
  - Start with: `PubMed`, `Europe PMC`
  - Then: `Semantic Scholar`, `Crossref`

- **Computer science / AI / ML**
  - Start with: `Semantic Scholar`, `arXiv`, `DBLP`, `OpenReview`
  - Enrich with: `Crossref`, `OpenAlex`

- **Biology / life sciences**
  - Start with: `PubMed`, `Europe PMC`, `bioRxiv`
  - Then: `Semantic Scholar`, `Crossref`

- **Known paper, DOI, or PDF hunt**
  - Start with: `Crossref`, `OpenAlex`, `Unpaywall`, `CORE`

### Example ranking heuristic

For future ranking logic, the MCP server or downstream AI client can apply domain-aware source weighting:

- Query contains terms like `biomechanics`, `rehabilitation`, `physiology`, `sports medicine`, `powerlifting`, `fatigue`, `injury`
  - Upweight: `PubMed`, `Europe PMC`, `Semantic Scholar`
  - Downweight: `DBLP`, `OpenReview`, `arXiv`

- Query contains terms like `transformer`, `LLM`, `benchmark`, `retrieval`, `compiler`, `database`
  - Upweight: `Semantic Scholar`, `arXiv`, `DBLP`, `OpenReview`
  - Downweight: `PubMed`

This improves relevance when multiple providers return valid but domain-misaligned results.
