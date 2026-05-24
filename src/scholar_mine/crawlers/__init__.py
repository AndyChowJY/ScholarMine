from scholar_mine.crawlers.base import BaseCrawler, PaperRecord, CrawlResult
from scholar_mine.crawlers.arxiv import ArxivCrawler
from scholar_mine.crawlers.semantic_scholar import SemanticScholarCrawler
from scholar_mine.crawlers.scihub import SciHubResolver
from scholar_mine.crawlers.crossref import CrossrefCrawler

__all__ = ["BaseCrawler", "PaperRecord", "CrawlResult", "ArxivCrawler", "SemanticScholarCrawler", "SciHubResolver", "CrossrefCrawler"]
