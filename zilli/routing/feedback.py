from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("zilli.routing.feedback")


@dataclass
class FeedbackRecord:
    request_id: str
    ppm_difficulty: float
    ppm_family: str
    selected_model: str
    strategy_tier: str
    actual_latency_ms: float
    actual_cost: float
    tokens_in: int = 0
    tokens_out: int = 0
    success: bool = True
    score: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


_DEFAULT_RATING_PROMPT = (
    "Rate the quality of the following response on a scale of 0.0 to 1.0.\n"
    "Consider: helpfulness, accuracy, relevance, completeness.\n\n"
    "Request: {request}\n\nResponse: {response}\n\nRating:"
)


class FeedbackCollector:
    def __init__(
        self,
        batch_size: int = 100,
        flush_interval_seconds: float = 5.0,
        persist_path: Optional[str] = None,
    ):
        self._batch_size = batch_size
        self._flush_interval = flush_interval_seconds
        self._queue: asyncio.Queue[FeedbackRecord] = asyncio.Queue()
        self._buffer: list[FeedbackRecord] = []
        self._path = Path(persist_path) if persist_path else None
        self._running = False

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        self._running = False
        await self.flush()

    def record(self, record: FeedbackRecord) -> None:
        self._queue.put_nowait(record)
        if self._queue.qsize() >= self._batch_size:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.flush())
            except RuntimeError:
                pass

    async def flush(self) -> None:
        while not self._queue.empty():
            try:
                record = self._queue.get_nowait()
                self._buffer.append(record)
            except asyncio.QueueEmpty:
                break

        if self._buffer:
            self._persist(self._buffer)
            self._buffer.clear()

    async def _flush_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Feedback flush error: %s", e)

    def _persist(self, records: list[FeedbackRecord]) -> None:
        if not self._path:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if self._path.exists() else "w"
            with self._path.open(mode, encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps({
                        "request_id": r.request_id,
                        "ppm_difficulty": r.ppm_difficulty,
                        "ppm_family": r.ppm_family,
                        "selected_model": r.selected_model,
                        "strategy_tier": r.strategy_tier,
                        "actual_latency_ms": r.actual_latency_ms,
                        "actual_cost": r.actual_cost,
                        "tokens_in": r.tokens_in,
                        "tokens_out": r.tokens_out,
                        "success": r.success,
                        "score": r.score,
                        "timestamp": r.timestamp,
                    }) + "\n")
        except Exception as e:
            logger.debug("Failed to persist feedback: %s", e)


_SCORE_RE = re.compile(r"Rating:\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


class FeedbackEvaluator:
    def __init__(
        self,
        rating_prompt: Optional[str] = None,
        llm_score_cache_size: int = 256,
    ):
        self._rating_prompt = rating_prompt or _DEFAULT_RATING_PROMPT
        self._llm_call_count = 0
        self._llm_fallback_count = 0
        self._llm_score_cache: dict[int, float] = {}
        self._llm_cache_size = llm_score_cache_size

    def auto_score(self, request: str, response: str) -> float:
        request_len = len(request)
        response_len = len(response)

        if response_len < 10:
            return 0.1

        score = 0.5

        if response_len > request_len * 0.5:
            score += 0.15
        if response_len > request_len * 2:
            score += 0.1

        score += min(response_len / 5000, 0.15)

        return max(0.0, min(1.0, score))

    async def llm_score(
        self,
        request: str,
        response: str,
        llm_generate: Callable[..., Any],
    ) -> float:
        cache_key = hash((request[:200].lower(), response[:200].lower()))
        cached = self._llm_score_cache.get(cache_key)
        if cached is not None:
            return cached

        prompt = self._rating_prompt.format(request=request, response=response)
        try:
            result = await llm_generate(prompt)
            if result and hasattr(result, "text"):
                text = result.text
            elif isinstance(result, str):
                text = result
            else:
                self._llm_fallback_count += 1
                return self.auto_score(request, response)

            match = _SCORE_RE.search(text)
            if match:
                score = float(match.group(1))
                score = max(0.0, min(1.0, score))
                self._llm_call_count += 1
                self._cache_llm_score(cache_key, score)
                return score

            self._llm_fallback_count += 1
            return self.auto_score(request, response)
        except Exception:
            self._llm_fallback_count += 1
            return self.auto_score(request, response)

    def _cache_llm_score(self, key: int, score: float) -> None:
        if len(self._llm_score_cache) >= self._llm_cache_size:
            self._llm_score_cache.clear()
        self._llm_score_cache[key] = score

    def stats(self) -> dict:
        return {
            "llm_calls": self._llm_call_count,
            "llm_fallbacks": self._llm_fallback_count,
            "llm_cache_size": len(self._llm_score_cache),
        }
