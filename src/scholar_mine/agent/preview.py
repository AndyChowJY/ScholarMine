"""Preview renderer — display execution plan for user confirmation."""
from scholar_mine.utils.logger import Logger

log = Logger.get()

class PreviewRenderer:
    @staticmethod
    def render(plan) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("  ScholarMine Execution Plan")
        lines.append("=" * 60)
        lines.append(f"  Research: {plan.research_direction}")
        lines.append(f"  Domain: {plan.domain or 'auto-detected'}")
        lines.append(f"  Target papers: {plan.paper_count}")
        lines.append(f"  Keywords: {len(plan.keywords)} generated")
        lines.append("-" * 60)
        if plan.keywords:
            lines.append("  Sample keywords:")
            for kw in plan.keywords[:10]:
                lines.append(f"    \u2022 {kw}")
            if len(plan.keywords) > 10:
                lines.append(f"    ... and {len(plan.keywords)-10} more")
        lines.append("-" * 60)
        schema = plan.schema or {}
        fields = schema.get("fields", [])
        if fields:
            lines.append(f"  Extraction schema: {len(fields)} fields")
            for f in fields[:8]:
                lines.append(f"    \u2022 {f.get('name', f.get('key', '?'))}")
            if len(fields) > 8:
                lines.append(f"    ... and {len(fields)-8} more")
        lines.append("-" * 60)
        lines.append("  Pipeline stages:")
        lines.append("    1. Keyword generation (LLM)")
        lines.append("    2. Multi-platform crawl (20+ sources)")
        lines.append("    3. Filter & classify (PDF validation + relevance)")
        lines.append("    4. Batch extraction (40 papers/batch -> LLM)")
        lines.append("    5. Split & store (per-paper .md + summary .csv)")
        lines.append("=" * 60)
        return "\n".join(lines)

    @staticmethod
    def render_rich(plan):
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            console = Console()
            console.print(Panel.fit(PreviewRenderer.render(plan), title="ScholarMine Plan"))
        except ImportError:
            print(PreviewRenderer.render(plan))
