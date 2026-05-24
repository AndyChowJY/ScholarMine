"""ArXiv API crawler — search + direct PDF download."""
import asyncio
from typing import List, Optional
from pathlib import Path

import arxiv

from scholar_mine.crawlers.base import BaseCrawler, PaperRecord
from scholar_mine.utils.logger import Logger

log = Logger.get()

class ArxivCrawler(BaseCrawler):
    platform_name = "arxiv"

    async def search(self, keyword: str, max_results: int = 50) -> List[PaperRecord]:
        loop = asyncio.get_event_loop()
        try:
            client = arxiv.Client(page_size=min(max_results, 100), delay_seconds=1.0)
            search = arxiv.Search(
                query=keyword,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            results = await loop.run_in_executor(None, lambda: list(client.results(search)))
        except Exception as e:
            log.warning(f"arXiv search failed for '{keyword}': {e}")
            return []

        records = []
        for r in results:
            pdf_url = r.pdf_url or f"https://arxiv.org/pdf/{r.get_short_id()}.pdf"
            records.append(PaperRecord(
                title=r.title or "",
                authors=", ".join(a.name for a in r.authors[:5]) if r.authors else "",
                abstract=r.summary or "",
                doi=getattr(r, 'doi', None),
                year=r.published.year if r.published else None,
                journal="arXiv preprint",
                pdf_url=pdf_url,
                source_platform="arxiv",
                metadata={"arxiv_id": r.get_short_id(), "categories": list(r.categories)},
            ))
        return records
