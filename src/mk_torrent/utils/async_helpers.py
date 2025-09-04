#!/usr/bin/env python3
"""Async utilities for non-blocking operations"""

import asyncio
from collections.abc import Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class AsyncTorrentCreator:
    """Async wrapper for parallel torrent creation"""

    def __init__(self, creator_instance):
        self.creator = creator_instance
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def create_torrent_async(self, source_path: Path, output_path: Path) -> bool:
        """Create torrent in background thread"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self.creator.create_torrent_via_api, source_path, output_path
        )

    async def create_batch_async(
        self,
        paths: list[tuple[Path, Path]],
        progress_callback: Callable | None = None,
    ) -> list[bool]:
        """Create multiple torrents in parallel"""
        tasks = []
        for source_path, output_path in paths:
            task = self.create_torrent_async(source_path, output_path)
            tasks.append(task)

        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                f"Creating {len(tasks)} torrents...", total=len(tasks)
            )

            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                progress.advance(task_id)
                if progress_callback:
                    progress_callback(len(results), len(tasks))

        return results

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, *args):
        """Async context manager exit"""
        self.executor.shutdown(wait=True)

    def __enter__(self):
        """Regular context manager entry (for backwards compat)"""
        return self

    def __exit__(self, *args):
        """Regular context manager exit"""
        self.executor.shutdown(wait=True)


async def parallel_health_checks(configs: dict[str, dict]) -> list[tuple[str, bool]]:
    """Check multiple qBittorrent instances in parallel"""
    from ..api.qbittorrent import QBittorrentAPI

    async def check_one(name: str, config: dict) -> tuple[str, bool]:
        loop = asyncio.get_event_loop()
        api = QBittorrentAPI(
            config.get("host", "localhost"),
            config.get("port", 8080),
            config.get("username", "admin"),
            config.get("password", "adminadmin"),
            config.get("use_https", False),
        )

        # Run synchronous check in thread pool
        connected = await loop.run_in_executor(None, api.test_connection)
        return (name, connected[0])

    # Fix: configs is a Dict, iterate over items() not configs.items
    tasks = [check_one(name, cfg) for name, cfg in configs.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions and return only successful results
    return [
        (name, success)
        for result in results
        if isinstance(result, tuple)
        for name, success in [result]
    ]


def run_async_batch(paths: list[tuple[Path, Path]], creator) -> list[bool]:
    """Convenience function to run async batch from sync code"""

    async def _run():
        # Fix: Use async with for async context manager
        async with AsyncTorrentCreator(creator) as async_creator:
            return await async_creator.create_batch_async(paths)

    return asyncio.run(_run())
