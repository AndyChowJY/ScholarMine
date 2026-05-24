"""Sci-Hub PDF resolver — DOI to PDF via mirror sites."""
import asyncio
from typing import List, Optional
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup

from scholar_mine.crawlers.base import BaseCrawler, PaperRecord
from scholar_mine.utils.logger import Logger

log = Logger.get()

MIRRORS = [
    "https://sci-hub.se",
    "https://sci-hub.st",
    "https://sci-hub.ru",
]

class SciHubResolver(BaseCrawler):
    platform_name = "scihub"

    async def search(self, keyword: str, max_results: int = 50) -> List[PaperRecord]:
        return []

    async def resolve_pdf(self, doi: str, dest_dir: Path) -> Optional[Path]:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        for mirror in MIRRORS:
            try:
                url = f"{mirror}/{doi}"
                async with self.rate_limit():
                    session = await self._get_session()
                    async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                        if resp.status != 200:
                            continue
                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")
                        embed = soup.find("embed")
                        iframe = soup.find("iframe")
                        pdf_url = None
                        if embed and embed.get("src"):
                            pdf_url = embed["src"]
                        elif iframe and iframe.get("src"):
                            pdf_url = iframe["src"]

                        if pdf_url:
                            if pdf_url.startswith("//"):
                                pdf_url = "https:" + pdf_url
                            elif pdf_url.startswith("/"):
                                pdf_url = mirror + pdf_url

                            async with session.get(pdf_url) as pdf_resp:
                                if pdf_resp.status == 200 and "application/pdf" in pdf_resp.headers.get("content-type", ""):
                                    content = await pdf_resp.read()
                                    if len(content) > 5000:
                                        safe_doi = doi.replace("/", "_")[:80]
                                        dest = dest_dir / f"{safe_doi}.pdf"
                                        dest.write_bytes(content)
                                        log.info(f"Sci-Hub: downloaded {doi}")
                                        return dest
            except Exception as e:
                log.debug(f"Sci-Hub mirror {mirror} failed for {doi}: {e}")
                continue

        log.warning(f"Sci-Hub: all mirrors failed for {doi}")
        return None
