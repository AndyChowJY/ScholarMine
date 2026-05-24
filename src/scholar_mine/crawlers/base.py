"""Abstract base class for all crawler implementations."""

import asyncio
import hashlib
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from scholar_mine.utils.logger import Logger

log = Logger.get()


@dataclass
class PaperRecord:
    """Standardized paper record from any platform."""
    title: str
    authors: str = ""
    abstract: str = ""
    doi: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    pdf_url: Optional[str] = None
    source_platform: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        """Deduplication key: DOI if available, else title hash."""
        if self.doi:
            return f"doi:{self.doi.lower().strip()}"
        clean = "".join(c.lower() for c in self.title if c.isalnum())
        return f"title:{clean[:80]}"

    @property
    def slug(self) -> str:
        """Filesystem-safe short name from title."""
        import re
        slug = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff\-]', '_', self.title)
        return slug[:120]


@dataclass
class CrawlResult:
    """Aggregated result from a crawl run."""
    records: List[PaperRecord] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def unique_records(self) -> List[PaperRecord]:
        """Deduplicate by DOI/title."""
        seen = set()
        unique = []
        for r in self.records:
            if r.dedup_key not in seen:
                seen.add(r.dedup_key)
                unique.append(r)
        return unique


class BaseCrawler:
    """Abstract base class for academic paper crawlers.

    Subclasses must override search().
    Optionally override download_pdf() for platforms with direct PDF access.
    """

    platform_name: str = "base"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rate_limit_rps = self.config.get("rate_limit_rps", 1.0)
        self.timeout = self.config.get("timeout_secs", 30)
        self._last_request_time = 0.0
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                "User-Agent": self.config.get(
                    "user_agent", "ScholarMine/0.1"
                ),
            }
            self._session = aiohttp.ClientSession(
                timeout=timeout, headers=headers
            )
        return self._session

    @asynccontextmanager
    async def rate_limit(self):
        """Context manager that enforces rate limiting."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / self.rate_limit_rps if self.rate_limit_rps > 0 else 0
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        try:
            yield
        finally:
            self._last_request_time = time.monotonic()

    async def search(self, keyword: str, max_results: int = 50) -> List[PaperRecord]:
        """Search for papers matching keyword. Override in subclass."""
        raise NotImplementedError(
            f"{self.platform_name}: search() not implemented"
        )

    async def download_pdf(
        self, record: PaperRecord, dest_dir: Path
    ) -> Optional[Path]:
        """Download PDF for a paper. Override if platform supports it."""
        if not record.pdf_url:
            return None

        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{record.slug}.pdf"
        dest_path = dest_dir / filename

        if dest_path.exists() and dest_path.stat().st_size > 0:
            return dest_path

        try:
            async with self.rate_limit():
                session = await self._get_session()
                async with session.get(record.pdf_url) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        if len(content) > 1000:  # minimum valid PDF size
                            dest_path.write_bytes(content)
                            return dest_path
                        else:
                            log.warning(
                                f"{self.platform_name}: PDF too small "
                                f"({len(content)} bytes) for {record.doi or record.title[:50]}"
                            )
                    else:
                        log.debug(
                            f"{self.platform_name}: HTTP {resp.status} "
                            f"for {record.pdf_url}"
                        )
        except Exception as e:
            log.warning(
                f"{self.platform_name}: download failed for "
                f"{record.doi or record.title[:50]}: {e}"
            )

        return None

    async def close(self):
        """Clean up HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
