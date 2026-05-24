"""Milky 心跳监测。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

import asyncio
import time


class MilkyHeartbeatMonitor:
    """Milky 连接状态监测器。"""

    def __init__(
        self,
        logger: Any,
        on_timeout: Callable[[str], Awaitable[None]],
    ) -> None:
        self._logger = logger
        self._on_timeout = on_timeout
        self._last_event_at: float = 0.0
        self._interval_sec: float = 30.0
        self._self_id: str = ""
        self._check_task: Optional[asyncio.Task[None]] = None
        self._timeout_reported: bool = False

    async def start(self, self_id: str, default_interval_sec: float) -> None:
        normalized_self_id = str(self_id or "").strip()
        if normalized_self_id:
            self._self_id = normalized_self_id
        self._interval_sec = max(float(default_interval_sec or 30.0), 1.0)
        self._touch()
        if self._check_task is None or self._check_task.done():
            self._check_task = asyncio.create_task(
                self._check_loop(),
                name="milky_adapter.heartbeat_monitor",
            )

    async def stop(self) -> None:
        check_task = self._check_task
        self._check_task = None
        self._timeout_reported = False
        self._last_event_at = 0.0
        if check_task is not None:
            check_task.cancel()
            try:
                await check_task
            except asyncio.CancelledError:
                pass

    def touch(self) -> None:
        self._touch()

    def _touch(self) -> None:
        self._last_event_at = time.time()
        self._timeout_reported = False

    async def _check_loop(self) -> None:
        while True:
            await asyncio.sleep(max(self._interval_sec, 1.0))
            if self._last_event_at <= 0:
                continue

            elapsed_sec = time.time() - self._last_event_at
            if elapsed_sec <= self._interval_sec * 3:
                continue

            if self._timeout_reported:
                continue

            self._timeout_reported = True
            self._logger.error(f"Bot {self._self_id or 'unknown'} 可能发生了连接断开")
            try:
                await self._on_timeout(self._self_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.warning(f"Milky 心跳超时回调执行失败: {exc}")
