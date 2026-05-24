"""Crossref REST API crawler."""
from typing import List
import aiohttp
from scholar_mine.crawlers.base import BaseCrawler, PaperRecord
from scholar_mine.utils.logger import Logger

log = Logger.get()

class CrossrefCrawler(BaseCrawler):
    platform_name = "crossref"
    API_BASE = "https://api.crossref.org/works"

    async def search(self, keyword: str, max_results: int = 50) -> List[PaperRecord]:
        records = []
        rows = min(max_results, 100)
        params = {"query": keyword, "rows": rows, "offset": 0}

        async with self.rate_limit():
            session = await self._get_session()
            try:
                async with session.get(self.API_BASE, params=params) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    items = data.get("message", {}).get("items", [])
                    for item in items:
                        title_list = item.get("title", [])
                        title = title_list[0] if title_list else ""
                        author_list = item.get("author", []) or []
                        authors = ", ".join(
                            f"{a.get('given','')} {a.get('family','')}".strip()
                            for a in author_list[:5]
                        )
                        records.append(PaperRecord(
                            title=title,
                            authors=authors,
                            abstract=item.get("abstract", ""),
                            doi=item.get("DOI"),
                            year=item.get("created", {}).get("date-parts", [[None]])[0][0],
                            journal=(item.get("container-title", [""]) or [""])[0],
                            pdf_url=None,
                            source_platform="crossref",
                            metadata={"publisher": item.get("publisher", ""), "type": item.get("type", "")},
                        ))
            except Exception as e:
                log.warning(f"Crossref error: {e}")

        return records[:max_results]
