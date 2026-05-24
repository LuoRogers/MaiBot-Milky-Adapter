"""Milky 协议端传输层。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, Optional, Set, cast

import asyncio
import contextlib
import json

from .config import MilkyServerConfig

if TYPE_CHECKING:
    from aiohttp import ClientWebSocketResponse as AiohttpClientWebSocketResponse

try:
    from aiohttp import ClientSession, ClientTimeout, WSMsgType

    AIOHTTP_AVAILABLE = True
except ImportError:
    ClientSession = cast(Any, None)
    ClientTimeout = cast(Any, None)
    WSMsgType = cast(Any, None)
    AIOHTTP_AVAILABLE = False

if not TYPE_CHECKING:
    AiohttpClientWebSocketResponse = Any


class MilkyTransportClient:
    """Milky 协议端传输层客户端。

    负责：
    1. 通过 HTTP POST 调用 Milky API
    2. 通过 SSE 或 WebSocket 接收事件推送
    """

    def __init__(
        self,
        logger: Any,
        on_connection_opened: Callable[[], Coroutine[Any, Any, None]],
        on_connection_closed: Callable[[], Coroutine[Any, Any, None]],
        on_payload: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        self._logger = logger
        self._on_connection_opened = on_connection_opened
        self._on_connection_closed = on_connection_closed
        self._on_payload = on_payload
        self._server_config: Optional[MilkyServerConfig] = None
        self._connection_task: Optional[asyncio.Task[None]] = None
        self._background_tasks: Set[asyncio.Task[Any]] = set()
        self._session: Optional[ClientSession] = None
        self._ws: Optional[AiohttpClientWebSocketResponse] = None
        self._stop_requested: bool = False
        self._connection_active: bool = False

    @classmethod
    def is_available(cls) -> bool:
        return AIOHTTP_AVAILABLE

    def configure(self, server_config: MilkyServerConfig) -> None:
        self._server_config = server_config

    async def start(self) -> None:
        if not self.is_available():
            raise RuntimeError("Milky 适配器依赖 aiohttp，但当前环境未安装该依赖")
        if self._server_config is None:
            raise RuntimeError("Milky 适配器尚未配置 milky_server")
        if self._connection_task is not None and not self._connection_task.done():
            return

        self._stop_requested = False
        self._connection_task = asyncio.create_task(self._connection_loop(), name="milky_adapter.connection")

    async def stop(self) -> None:
        self._stop_requested = True
        connection_task = self._connection_task
        self._connection_task = None

        ws = self._ws
        if ws is not None and not ws.closed:
            with contextlib.suppress(Exception):
                await ws.close()
        self._ws = None

        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

        if connection_task is not None:
            connection_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await connection_task

        await self._cancel_background_tasks()
        await self._notify_connection_closed()

    async def call_action(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """通过 HTTP POST 调用 Milky API。

        Args:
            action_name: API 名称。
            params: API 参数。

        Returns:
            Dict[str, Any]: Milky 返回的响应字典。
        """
        server_config = self._server_config
        if server_config is None:
            raise RuntimeError("Milky is not configured")

        url = server_config.build_api_url(action_name)
        headers = self._build_headers(server_config)

        try:
            timeout = ClientTimeout(total=server_config.action_timeout_sec)
            async with ClientSession(timeout=timeout) as session:
                async with session.post(url, json=params, headers=headers) as response:
                    if response.status == 401:
                        raise RuntimeError("Milky API 认证失败，请检查 access_token")
                    if response.status == 404:
                        raise RuntimeError(f"Milky API 不存在: {action_name}")
                    if response.status != 200:
                        raise RuntimeError(f"Milky API 调用失败: HTTP {response.status}")

                    result = await response.json()
                    return result if isinstance(result, dict) else {"status": "failed", "message": "Invalid response"}
        except asyncio.CancelledError:
            raise
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Milky API 调用异常: {action_name} error={exc}") from exc

    async def _connection_loop(self) -> None:
        while not self._stop_requested:
            server_config = self._server_config
            if server_config is None:
                return

            try:
                if server_config.event_mode == "websocket":
                    await self._connect_websocket(server_config)
                else:
                    await self._connect_sse(server_config)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.warning(
                    f"Milky 适配器连接失败: {exc}"
                    f"{self._build_reconnect_hint(server_config)}"
                )
            finally:
                self._ws = None
                if self._session is not None and not self._session.closed:
                    await self._session.close()
                self._session = None
                await self._notify_connection_closed()

            if self._stop_requested:
                break

            await asyncio.sleep(server_config.reconnect_delay_sec)

    async def _connect_websocket(self, server_config: MilkyServerConfig) -> None:
        """通过 WebSocket 接收事件。"""
        assert ClientSession is not None
        assert ClientTimeout is not None

        ws_url = server_config.build_event_ws_url()
        headers = self._build_headers(server_config)
        timeout = ClientTimeout(total=None, connect=10)

        self._logger.info(f"Milky 适配器正在通过 WebSocket 连接事件流: {ws_url}")
        self._session = ClientSession(headers=headers, timeout=timeout)

        try:
            async with self._session.ws_connect(ws_url) as ws:
                self._ws = ws
                self._logger.info(f"Milky 适配器已连接事件流 (WebSocket): {ws_url}")
                await self._ws_receive_loop(ws)
        finally:
            self._ws = None

    async def _connect_sse(self, server_config: MilkyServerConfig) -> None:
        """通过 SSE 接收事件。"""
        assert ClientSession is not None
        assert ClientTimeout is not None

        event_url = server_config.build_event_url()
        headers = self._build_headers(server_config)
        headers["Accept"] = "text/event-stream"
        timeout = ClientTimeout(total=None, connect=10)

        self._logger.info(f"Milky 适配器正在通过 SSE 连接事件流: {event_url}")
        self._session = ClientSession(headers=headers, timeout=timeout)

        try:
            async with self._session.get(event_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"SSE 连接失败: HTTP {response.status}")
                self._logger.info(f"Milky 适配器已连接事件流 (SSE): {event_url}")
                await self._sse_receive_loop(response)
        finally:
            pass

    async def _ws_receive_loop(self, ws: AiohttpClientWebSocketResponse) -> None:
        """WebSocket 事件接收循环。"""
        assert WSMsgType is not None

        bootstrap_task = self._create_background_task(
            self._notify_connection_opened(),
            "milky_adapter.bootstrap",
        )
        try:
            async for ws_message in ws:
                if ws_message.type != WSMsgType.TEXT:
                    if ws_message.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                        break
                    continue

                payload = self._parse_json_message(ws_message.data)
                if payload is None:
                    continue

                self._create_background_task(self._on_payload(payload), "milky_adapter.payload")
        finally:
            if bootstrap_task is not None and not bootstrap_task.done():
                bootstrap_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await bootstrap_task

    async def _sse_receive_loop(self, response: Any) -> None:
        """SSE 事件接收循环。"""
        bootstrap_task = self._create_background_task(
            self._notify_connection_opened(),
            "milky_adapter.bootstrap",
        )
        try:
            buffer = ""
            async for data, end_of_http_chunk in response.content.iter_chunks():
                if not data:
                    continue
                text = data.decode("utf-8", errors="replace")
                buffer += text

                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    event_data = self._extract_sse_data(event_block)
                    if not event_data:
                        continue

                    payload = self._parse_json_message(event_data)
                    if payload is None:
                        continue

                    self._create_background_task(self._on_payload(payload), "milky_adapter.payload")
        finally:
            if bootstrap_task is not None and not bootstrap_task.done():
                bootstrap_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await bootstrap_task

    @staticmethod
    def _extract_sse_data(event_block: str) -> Optional[str]:
        """从 SSE 事件块中提取 data 字段。"""
        data_lines = []
        for line in event_block.split("\n"):
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif line.startswith("data: "):
                data_lines.append(line[6:])
        if not data_lines:
            return None
        return "\n".join(data_lines)

    def _build_headers(self, server_config: MilkyServerConfig) -> Dict[str, str]:
        if server_config.token:
            return {"Authorization": f"Bearer {server_config.token}"}
        return {}

    def _build_reconnect_hint(self, server_config: MilkyServerConfig) -> str:
        if self._stop_requested:
            return ""
        return f"；将在 {server_config.reconnect_delay_sec:g} 秒后重连"

    def _create_background_task(self, coroutine: Coroutine[Any, Any, Any], name: str) -> asyncio.Task[Any]:
        task = asyncio.create_task(coroutine, name=name)
        self._background_tasks.add(task)
        task.add_done_callback(self._handle_background_task_completion)
        return task

    def _handle_background_task_completion(self, task: asyncio.Task[Any]) -> None:
        self._background_tasks.discard(task)
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            self._logger.error(f"Milky 适配器后台任务异常: {exception}", exc_info=True)

    async def _cancel_background_tasks(self) -> None:
        background_tasks = list(self._background_tasks)
        for task in background_tasks:
            task.cancel()
        if background_tasks:
            with contextlib.suppress(Exception):
                await asyncio.gather(*background_tasks, return_exceptions=True)
        self._background_tasks.clear()

    async def _notify_connection_opened(self) -> None:
        if self._connection_active:
            return
        self._connection_active = True
        try:
            await self._on_connection_opened()
        except Exception as exc:
            self._logger.warning(f"Milky 适配器连接建立回调失败: {exc}")

    async def _notify_connection_closed(self) -> None:
        if not self._connection_active:
            return
        self._connection_active = False
        try:
            await self._on_connection_closed()
        except Exception as exc:
            self._logger.warning(f"Milky 适配器断连回调失败: {exc}")

    def _parse_json_message(self, data: Any) -> Optional[Dict[str, Any]]:
        try:
            payload = json.loads(str(data))
        except Exception as exc:
            self._logger.warning(f"Milky 适配器解析 JSON 载荷失败: {exc}")
            return None
        return payload if isinstance(payload, dict) else None
