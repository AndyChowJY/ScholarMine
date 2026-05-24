"""Semantic Scholar API crawler."""
import asyncio
from typing import List
from pathlib import Path

import aiohttp

from scholar_mine.crawlers.base import BaseCrawler, PaperRecord
from scholar_mine.utils.logger import Logger

log = Logger.get()

class SemanticScholarCrawler(BaseCrawler):
    platform_name = "semantic_scholar"
    API_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(self, keyword: str, max_results: int = 50) -> List[PaperRecord]:
        fields = "title,authors,abstract,year,externalIds,openAccessPdf,journal,publicationDate"
        records = []
        offset = 0
        limit = min(100, max_results)

        async with self.rate_limit():
            session = await self._get_session()
            while len(records) < max_results:
                params = {"query": keyword, "offset": offset, "limit": limit, "fields": fields}
                try:
                    async with session.get(self.API_BASE, params=params) as resp:
                        if resp.status != 200:
                            break
                        data = await resp.json()
                        papers = data.get("data", [])
                        if not papers:
                            break
                        for p in papers:
                            ext = p.get("externalIds", {}) or {}
                            oa = p.get("openAccessPdf", {}) or {}
                            authors_list = p.get("authors", []) or []
                            authors_str = ", ".join(
                                a.get("name", "") for a in authors_list[:5]
                            )
                            records.append(PaperRecord(
                                title=p.get("title", ""),
                                authors=authors_str,
                                abstract=p.get("abstract", ""),
                                doi=ext.get("DOI"),
                                year=p.get("year"),
                                journal=(p.get("journal", {}) or {}).get("name", ""),
                                pdf_url=oa.get("url"),
                                source_platform="semantic_scholar",
                                metadata={"paper_id": p.get("paperId"), "citation_count": p.get("citationCount")},
                            ))
                        offset += limit
                        if offset >= data.get("total", 0):
                            break
                except Exception as e:
                    log.warning(f"Semantic Scholar error: {e}")
                    break
                await asyncio.sleep(0.5)

        return records[:max_results]
