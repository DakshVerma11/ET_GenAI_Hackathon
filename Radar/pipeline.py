"""
Pipeline Orchestrator

Runs all fetchers on their configured intervals using APScheduler.
Also registers the signal broadcaster so new signals are pushed over WebSocket.

Usage:
  python pipeline.py              (standalone — for testing)
  Called by api.py on startup     (integrated with FastAPI)
"""
import asyncio
import logging
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from rich.console import Console
from rich.table import Table

from init_db import get_engine, get_session_factory
from fetchers import FilingsFetcher, BulkDealsFetcher, InsiderTradingFetcher, IndicesFetcher
from generator import set_broadcaster
from websocket import broadcaster
from settings import settings

logger = logging.getLogger(__name__)
console = Console()


class Pipeline:
    def __init__(self):
        self.engine = get_engine()
        self.session_factory = get_session_factory(self.engine)
        self.scheduler = AsyncIOScheduler()
        self.broadcaster = broadcaster

        # Register the WebSocket broadcaster so signals get pushed live
        set_broadcaster(broadcaster)

        # Initialize fetchers
        self.fetchers = {
            "filings": FilingsFetcher(self.session_factory),
            "bulk": BulkDealsFetcher(self.session_factory),
            "insider": InsiderTradingFetcher(self.session_factory),
            "indices": IndicesFetcher(self.session_factory),
        }

    def _schedule_fetcher(self, name: str, fetcher, interval_seconds: int):
        async def job():
            logger.info(f"Running fetcher: {name}")
            stats = await fetcher.run()
            if stats.get("events_new", 0) > 0:
                logger.info(
                    f"{name}: +{stats['events_new']} new events, "
                    f"{stats['signals_generated']} signals generated"
                )
            if stats.get("error"):
                logger.error(f"{name} error: {stats['error']}")

        self.scheduler.add_job(
            job,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=name,
            name=f"{name} fetcher",
            replace_existing=True,
            max_instances=1,           # prevent overlap if a run takes too long
            misfire_grace_time=30,
        )
        logger.info(f"Scheduled {name} every {interval_seconds}s")

    async def start(self):
        """Start all fetchers. Called from FastAPI lifespan."""
        console.print("[bold green]Opportunity Radar Pipeline starting...[/bold green]")

        self._schedule_fetcher("filings", self.fetchers["filings"], settings.fetch_interval_filings)
        self._schedule_fetcher("bulk", self.fetchers["bulk"], settings.fetch_interval_bulk)
        self._schedule_fetcher("insider", self.fetchers["insider"], settings.fetch_interval_insider)
        self._schedule_fetcher("indices", self.fetchers["indices"], settings.fetch_interval_indices)

        self.scheduler.start()

        table = Table(title="Pipeline Schedule", show_header=True)
        table.add_column("Fetcher", style="cyan")
        table.add_column("Interval", style="green")
        table.add_column("Source")
        table.add_row("filings", f"{settings.fetch_interval_filings}s", "NSE /corporates/filings")
        table.add_row("bulk", f"{settings.fetch_interval_bulk}s", "NSE /corporates/bulk-deals + block-deals")
        table.add_row("insider", f"{settings.fetch_interval_insider}s", "NSE /corporates/insider-trading")
        table.add_row("indices", f"{settings.fetch_interval_indices}s", "NSE /allIndices")
        console.print(table)

        # Run all fetchers once immediately on startup (don't wait for first interval)
        console.print("[yellow]Running initial fetch cycle...[/yellow]")
        tasks = [fetcher.run() for fetcher in self.fetchers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        console.print("[bold green]Initial fetch complete[/bold green]")

    async def stop(self):
        """Graceful shutdown."""
        self.scheduler.shutdown(wait=False)
        await self.engine.dispose()
        logger.info("Pipeline stopped")


# Standalone mode
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    async def main():
        from init_db import init_db
        await init_db()

        pipeline = Pipeline()
        await pipeline.start()

        console.print("[bold]Pipeline running. Press Ctrl+C to stop.[/bold]")
        try:
            while True:
                await asyncio.sleep(60)
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[red]Shutting down...[/red]")
            await pipeline.stop()

    asyncio.run(main())