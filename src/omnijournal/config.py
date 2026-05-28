"""Environment-based configuration."""

from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Read configuration from environment variables.

    Entirely optional — nothing must be set for base functionality (Tier 1 sources).
    """

    def __init__(self) -> None:
        # Optional polite-use email addresses
        self.openalex_email: str | None = os.getenv("OPENALEX_EMAIL")
        self.crossref_email: str | None = os.getenv("CROSSREF_EMAIL")

        # Optional API keys
        self.semantic_scholar_api_key: str | None = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

        # Unpaywall (for OA resolution)
        self.unpaywall_email: str | None = os.getenv("UNPAYWALL_EMAIL")

        # Data / cache directories
        data_root = os.getenv(
            "OMNIJOURNAL_DATA_DIR",
            os.path.join(os.path.expanduser("~"), ".hermes", "omnijournal"),
        )
        self.data_dir = Path(data_root)
        self.cache_dir = self.data_dir / "cache"
        self.download_dir = self.data_dir / "downloads"

        # Timing
        self.provider_timeout: int = int(os.getenv("OMNIJOURNAL_PROVIDER_TIMEOUT", "30"))
        self.max_parallel_providers: int = int(
            os.getenv("OMNIJOURNAL_MAX_PARALLEL", "6")
        )

    def ensure_dirs(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
