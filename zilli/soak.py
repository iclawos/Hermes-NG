from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("zilli.soak")


@dataclass
class SoakHealth:
    started_at: float = field(default_factory=time.time)
    cycles_completed: int = 0
    cycles_failed: int = 0
    consecutive_failures: int = 0
    last_cycle_at: float = 0.0
    last_error: str = ""
    last_champion: str = ""
    max_consecutive_failures: int = 3

    @property
    def uptime_hours(self) -> float:
        return (time.time() - self.started_at) / 3600

    @property
    def healthy(self) -> bool:
        return self.consecutive_failures < self.max_consecutive_failures

    def to_dict(self) -> dict[str, Any]:
        return {
            "uptime_hours": round(self.uptime_hours, 2),
            "cycles_completed": self.cycles_completed,
            "cycles_failed": self.cycles_failed,
            "consecutive_failures": self.consecutive_failures,
            "healthy": self.healthy,
            "last_cycle_at": self.last_cycle_at,
            "last_error": self.last_error,
            "last_champion": self.last_champion,
        }


class SoakRunner:
    """Long-running end-to-end self-evolution loop for production validation.

    Runs EvolveToTrainPipeline continuously with:
    - crash recovery (per-cycle exception isolation + exponential backoff)
    - health monitoring (JSON status file + JSONL metrics)
    - graceful stop (file-based stop signal or max_duration)

    Designed for the v1.0.0 requirement: ≥7 days continuous operation.
    """

    def __init__(
        self,
        pipeline,
        interval_sec: float = 300.0,
        status_path: str = "./soak_status.json",
        metrics_path: str = "./soak_metrics.jsonl",
        max_consecutive_failures: int = 5,
        backoff_base_sec: float = 60.0,
    ):
        self.pipeline = pipeline
        self.interval = interval_sec
        self.status_path = Path(status_path)
        self.metrics_path = Path(metrics_path)
        self.max_consecutive_failures = max_consecutive_failures
        self.backoff_base = backoff_base_sec
        self.health = SoakHealth(max_consecutive_failures=max_consecutive_failures)
        self._running = False

    async def run(
        self,
        max_duration_sec: Optional[float] = None,
        stop_file: Optional[str] = None,
    ) -> SoakHealth:
        self._running = True
        self._deadline = time.time() + max_duration_sec if max_duration_sec else None

        logger.info("Soak runner started (interval=%.0fs)", self.interval)
        self._write_status()

        while self._running:
            if self._deadline and time.time() >= self._deadline:
                logger.info("Soak runner reached max duration")
                break
            if stop_file and Path(stop_file).exists():
                logger.info("Soak runner stopped by stop file: %s", stop_file)
                break

            cycle_start = time.monotonic()
            try:
                records = await self.pipeline.run_cycle()
                self.health.cycles_completed += 1
                self.health.consecutive_failures = 0
                failed = [r for r in records if not r.success]
                if failed:
                    logger.warning("Cycle had %d failed stages", len(failed))
                summary = self.pipeline.summary()
                self.health.last_champion = summary.get("champion_model", "")
                self._append_metrics({
                    "ts": time.time(),
                    "event": "cycle_ok",
                    "stages": len(records),
                    "failed_stages": len(failed),
                    "duration_s": round(time.monotonic() - cycle_start, 2),
                    "champion": self.health.last_champion,
                })
            except asyncio.CancelledError:
                logger.info("Soak runner cancelled")
                break
            except Exception as e:
                self.health.cycles_failed += 1
                self.health.consecutive_failures += 1
                self.health.last_error = str(e)
                logger.error(
                    "Soak cycle failed (%d/%d consecutive): %s",
                    self.health.consecutive_failures, self.max_consecutive_failures, e,
                    exc_info=True,
                )
                self._append_metrics({
                    "ts": time.time(),
                    "event": "cycle_error",
                    "error": str(e)[:500],
                    "consecutive": self.health.consecutive_failures,
                })
                if self.health.consecutive_failures >= self.max_consecutive_failures:
                    logger.critical("Too many consecutive failures — stopping soak runner")
                    break
                backoff = min(self.backoff_base * (2 ** self.health.consecutive_failures), 1800)
                await self._sleep_with_status(backoff)
                continue

            self.health.last_cycle_at = time.time()
            self._write_status()
            await self._sleep_with_status(self.interval)

        self._running = False
        self._write_status()
        logger.info(
            "Soak runner stopped: %d ok / %d failed cycles, uptime %.1fh",
            self.health.cycles_completed, self.health.cycles_failed,
            self.health.uptime_hours,
        )
        return self.health

    async def _sleep_with_status(self, seconds: float) -> None:
        elapsed = 0.0
        step = min(seconds, 0.5)
        while elapsed < seconds and self._running:
            if self._deadline and time.time() >= self._deadline:
                return
            await asyncio.sleep(step)
            elapsed += step

    def _write_status(self) -> None:
        try:
            self.status_path.write_text(json.dumps(self.health.to_dict(), indent=2))
        except OSError as e:
            logger.warning("Failed to write soak status: %s", e)

    def _append_metrics(self, entry: dict) -> None:
        try:
            self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metrics_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            logger.warning("Failed to append soak metrics: %s", e)

    def stop(self) -> None:
        self._running = False


__all__ = ["SoakRunner", "SoakHealth"]
