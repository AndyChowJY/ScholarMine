"""ScholarMine CLI — one command to rule them all.

Usage:
    scholarmine plan "research topic here"
    scholarmine run [--yes]
    scholarmine resume
    scholarmine status
"""

import sys
from pathlib import Path
from typing import Optional

import click
import yaml
from dotenv import load_dotenv

from scholar_mine.utils.logger import Logger

load_dotenv()


@click.group()
@click.version_option(version="0.1.0", prog_name="ScholarMine")
@click.option("--config", "-c", default=None, help="Path to config file")
@click.option("--workspace", "-w", default=".", help="Workspace directory")
@click.pass_context
def main(ctx, config: Optional[str], workspace: str):
    """ScholarMine — Agent-Orchestrated Academic Literature Mining Pipeline.

    Natural language → keywords → crawl 20 platforms → filter → extract → store.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["workspace"] = Path(workspace).resolve()
    ctx.obj["workspace"].mkdir(parents=True, exist_ok=True)
    Logger(
        log_dir=str(ctx.obj["workspace"] / "logs"),
        level="INFO",
    )


@main.command()
@click.argument("topic", nargs=-1)
@click.option("--count", "-n", default=1500, help="Target paper count")
@click.option("--keywords-only", is_flag=True, help="Only generate keywords, skip crawl")
@click.option("--schema", "-s", default=None, help="Schema ID or path to YAML")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def plan(ctx, topic, count, keywords_only, schema, yes):
    """Plan a literature mining run from a natural language topic.

    Example:
        scholarmine plan "single-atom catalysts for CO2 reduction 2023-2025"
        scholarmine plan "MOF-derived Ni catalysts for electrocatalysis" -n 2000 -y
    """
    topic_str = " ".join(topic)
    if not topic_str.strip():
        click.echo("Error: Please provide a research topic.", err=True)
        sys.exit(1)

    click.echo(f"\n🔍 ScholarMine planning for: {topic_str}\n")

    try:
        from scholar_mine.agent.planner import ResearchPlanner
        from scholar_mine.agent.preview import PreviewRenderer
        from scholar_mine.llm.client import LLMClient

        llm = LLMClient()
        planner = ResearchPlanner(llm)
        plan_result = planner.plan(topic_str, paper_count=count)

        # Render preview
        click.echo(PreviewRenderer.render(plan_result))

        if not (yes or click.confirm("\nProceed with this plan?")):
            click.echo("Cancelled.")
            return

        # Write config to workspace
        from scholar_mine.agent.config_generator import ConfigGenerator
        gen = ConfigGenerator(ctx.obj["workspace"])
        config_path = gen.generate(plan_result)
        click.echo(f"\n✅ Config written to: {config_path}")

        if keywords_only:
            click.echo(f"\nKeywords ({len(plan_result.keywords)}):")
            for kw in plan_result.keywords:
                click.echo(f"  • {kw}")
            return

        # Optionally launch pipeline
        if click.confirm("Launch pipeline now?"):
            from scholar_mine.pipeline.orchestrator import Orchestrator
            orch = Orchestrator(config_path, ctx.obj["workspace"])
            success = orch.run()
            if success:
                click.echo("\n🎉 Pipeline completed successfully!")
            else:
                click.echo("\n⚠️  Pipeline completed with errors. Check logs/.")

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option("--config", "-c", default=None, help="Path to pipeline config")
@click.option("--stage", "-s", type=int, default=1, help="Start from stage (1-5)")
@click.pass_context
def run(ctx, config, stage):
    """Run pipeline from a config file."""
    config_path = Path(config) if config else ctx.obj["workspace"] / "pipeline_config.yaml"
    if not config_path.exists():
        click.echo(f"Error: Config file not found: {config_path}", err=True)
        click.echo("Run 'scholarmine plan' first, or provide --config.", err=True)
        sys.exit(1)

    click.echo(f"🚀 Running pipeline from: {config_path}")
    from scholar_mine.pipeline.orchestrator import Orchestrator
    orch = Orchestrator(config_path, ctx.obj["workspace"])
    success = orch.run(start_stage=stage)
    if success:
        click.echo("\n🎉 Pipeline completed!")
    else:
        click.echo("\n⚠️  Pipeline completed with errors.")


@main.command()
@click.pass_context
def status(ctx):
    """Show pipeline status."""
    from scholar_mine.utils.checkpoint import Checkpoint
    cp = Checkpoint(ctx.obj["workspace"])
    summary = cp.status_summary()
    click.echo("\nPipeline Status:")
    for stage, st in summary.items():
        icon = "✅" if st == "ok" else "⏳"
        click.echo(f"  Stage {stage}: {icon} {st}")


@main.command()
@click.pass_context
def resume(ctx):
    """Resume pipeline from last checkpoint."""
    from scholar_mine.utils.checkpoint import Checkpoint
    cp = Checkpoint(ctx.obj["workspace"])
    for stage in range(1, 6):
        if not cp.is_done(stage):
            click.echo(f"Resuming from stage {stage}...")
            config_path = ctx.obj["workspace"] / "pipeline_config.yaml"
            from scholar_mine.pipeline.orchestrator import Orchestrator
            orch = Orchestrator(config_path, ctx.obj["workspace"])
            orch.run(start_stage=stage)
            return
    click.echo("All stages complete. Nothing to resume.")



@main.command()
@click.option("--interval", "-i", type=float, default=5.0, help="Check interval in seconds")
@click.option("--stall", type=float, default=30.0, help="Stall timeout in minutes")
@click.pass_context
def guard(ctx, interval, stall):
    """Run pipeline watchdog — monitor for error loops and stalls."""
    click.echo(f"🛡️  Guard watching {ctx.obj['workspace']} (interval={interval}s, stall={stall}m)")
    from scholar_mine.utils.guard import run_guard
    try:
        run_guard(str(ctx.obj["workspace"]), interval=interval, stall_timeout_mins=stall)
    except KeyboardInterrupt:
        click.echo("nGuard stopped.")


if __name__ == "__main__":
    main()