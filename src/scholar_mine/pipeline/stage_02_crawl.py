"""Stage 2: Multi-platform parallel crawl + PDF download."""
import asyncio, json
from pathlib import Path
from typing import List, Dict, Any

from scholar_mine.crawlers.arxiv import ArxivCrawler
from scholar_mine.crawlers.semantic_scholar import SemanticScholarCrawler
from scholar_mine.crawlers.crossref import CrossrefCrawler
from scholar_mine.crawlers.scihub import SciHubResolver
from scholar_mine.crawlers.base import PaperRecord, CrawlResult
from scholar_mine.utils.logger import Logger
from scholar_mine.utils.validators import fuzzy_dedup_key

log = Logger.get()

class Stage02Crawl:
    def __init__(self, config: dict, workspace: Path):
        self.config = config
        self.workspace = Path(workspace)
        self.download_dir = workspace / "downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.max_papers = config.get("pipeline", {}).get("paper_count", 1500)
        self.crawler_config = config.get("crawler", {})

    async def run(self) -> dict:
        keywords_path = self.workspace / "keywords.jsonl"
        if not keywords_path.exists():
            log.error("keywords.jsonl not found — run Stage 1 first")
            return {"error": "keywords not found"}

        keywords = []
        with open(keywords_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    keywords.append(json.loads(line)["keyword"])

        log.info(f"Crawling with {len(keywords)} keywords, target {self.max_papers} papers")

        # Initialize crawlers
        crawlers = [ArxivCrawler(), SemanticScholarCrawler(), CrossrefCrawler()]
        scihub = SciHubResolver()

        # Search all platforms concurrently
        all_records: List[PaperRecord] = []
        for kw in keywords[:15]:  # Use top 15 keywords to avoid excessive API calls
            tasks = [c.search(kw, max_results=100) for c in crawlers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_records.extend(r)
                elif isinstance(r, Exception):
                    log.warning(f"Crawl error for '{kw}': {r}")

        # Deduplicate
        seen = set()
        unique: List[PaperRecord] = []
        for r in all_records:
            key = r.dedup_key or fuzzy_dedup_key(r.title)
            if key and key not in seen:
                seen.add(key)
                unique.append(r)

        unique = unique[:self.max_papers]
        log.info(f"Found {len(all_records)} total, {len(unique)} unique after dedup")

        # Download PDFs
        downloaded = 0
        for r in unique:
            if r.pdf_url:
                path = await ArxivCrawler().download_pdf(r, self.download_dir)
                if path:
                    downloaded += 1
                    continue
            if r.doi:
                path = await scihub.resolve_pdf(r.doi, self.download_dir)
                if path:
                    downloaded += 1

        # Save manifest
        manifest = [{"title": r.title, "doi": r.doi, "pdf_url": r.pdf_url,
                      "source": r.source_platform, "downloaded": bool(r.pdf_url)}
                     for r in unique]
        manifest_path = self.workspace / "manifest.jsonl"
        with open(manifest_path, "w", encoding="utf-8") as f:
            for m in manifest:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")

        return {"total_found": len(all_records), "unique": len(unique),
                "downloaded_pdfs": downloaded, "manifest": str(manifest_path)}
