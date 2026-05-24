"""Milky 事件路由协调器。"""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Protocol

import asyncio

from ..config import MilkyPluginSettings
from ..types import MilkyPayloadDict
from .bundle import MilkyRuntimeBundle


class _GatewayCapabilityProtocol(Protocol):
    """插件网关能力协议。"""

    async def route_message(
        self,
        gateway_name: str,
        message: Dict[str, Any],
        *,
        route_metadata: Optional[Dict[str, Any]] = None,
        external_message_id: str = "",
        dedupe_key: str = "",
    ) -> bool:
        """向 Host 注入一条消息。"""
        ...


class MilkyEventRouter:
    """协调 Milky 运行时组件处理各类平台事件。"""

    def __init__(
        self,
        gateway_capability: _GatewayCapabilityProtocol,
        logger: Any,
        gateway_name: str,
        load_settings: Callable[[], MilkyPluginSettings],
    ) -> None:
        self._gateway_capability = gateway_capability
        self._logger = logger
        self._gateway_name = gateway_name
        self._load_settings = load_settings
        self._runtime: Optional[MilkyRuntimeBundle] = None

    def bind_runtime(self, runtime: MilkyRuntimeBundle) -> None:
        self._runtime = runtime

    def reset_caches(self) -> None:
        pass

    async def handle_transport_payload(self, payload: MilkyPayloadDict) -> None:
        """处理来自传输层的事件载荷。"""
        event_type = str(payload.get("event_type") or "").strip()
        event_data = payload.get("data", {})
        if not isinstance(event_data, Mapping):
            event_data = {}
        event_data = dict(event_data)

        runtime = self._require_runtime()
        runtime.heartbeat_monitor.touch()

        if event_type == "message_receive":
            await self.handle_inbound_message(event_data, payload)
            return

        await self.handle_notice_event(event_type, event_data, payload)

    async def handle_inbound_message(
        self,
        event_data: Dict[str, Any],
        raw_payload: MilkyPayloadDict,
    ) -> None:
        """处理 Milky 消息接收事件并注入 Host。"""
        runtime = self._require_runtime()
        settings = self._load_settings()

        self_id = str(raw_payload.get("self_id") or "").strip()
        sender_id = str(event_data.get("sender_id") or "").strip()
        if not sender_id:
            return

        message_scene = str(event_data.get("message_scene") or "").strip()
        peer_id = str(event_data.get("peer_id") or "").strip()
        group_id = peer_id if message_scene == "group" else ""

        if self_id and sender_id == self_id and settings.filters.ignore_self_message:
            return
        if not runtime.chat_filter.is_inbound_chat_allowed(sender_id, group_id, settings.chat):
            return

        try:
            message_dict = await runtime.inbound_codec.build_message_dict(event_data, self_id)
        except ValueError as exc:
            self._logger.warning(f"Milky 入站消息格式不受支持，已丢弃: {exc}")
            return

        plain_text = str(message_dict.get("processed_plain_text") or "").strip()
        if not runtime.regex_filter.is_message_allowed(plain_text, settings.filters):
            return

        route_metadata = self._build_route_metadata(self_id, settings.milky_server.connection_id)
        message_seq = event_data.get("message_seq")
        external_message_id = f"{message_scene}-{peer_id}-{message_seq}" if message_seq is not None else ""
        dedupe_key = external_message_id

        accepted = await self._gateway_capability.route_message(
            gateway_name=self._gateway_name,
            message=message_dict,
            route_metadata=route_metadata,
            external_message_id=external_message_id,
            dedupe_key=dedupe_key,
        )
        if not accepted:
            self._logger.debug(f"Host 丢弃了 Milky 入站消息: {external_message_id or '无消息 ID'}")

    async def handle_notice_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        raw_payload: MilkyPayloadDict,
    ) -> None:
        """处理 Milky 通知事件并注入 Host。"""
        runtime = self._require_runtime()
        settings = self._load_settings()

        self_id = str(raw_payload.get("self_id") or "").strip()

        message_dict = await runtime.notice_codec.build_notice_message_dict(event_type, event_data)
        if message_dict is None:
            return

        route_metadata = self._build_route_metadata(self_id, settings.milky_server.connection_id)
        dedupe_key = runtime.notice_codec.build_notice_dedupe_key(event_type, event_data) or ""

        accepted = await self._gateway_capability.route_message(
            gateway_name=self._gateway_name,
            message=message_dict,
            route_metadata=route_metadata,
            external_message_id="",
            dedupe_key=dedupe_key,
        )
        if not accepted:
            self._logger.debug(f"Host 丢弃了 Milky 通知事件: {event_type} {dedupe_key}")

    async def bootstrap_adapter_runtime_state(self) -> None:
        """在连接建立后主动获取账号信息并激活消息网关路由。"""
        runtime = self._require_runtime()
        settings = self._load_settings()

        max_attempts = 3
        last_error: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                login_info = await runtime.query_service.get_login_info()
                self_id = self._extract_self_id_from_login_response(login_info)
                base_url = f"http://{settings.milky_server.host}:{settings.milky_server.port}"
                await runtime.runtime_state.report_connected(
                    self_id, settings.milky_server.connection_id, base_url
                )
                self._logger.info(f"Milky 消息网关已激活: account_id={self_id}")
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                self._logger.warning(f"Milky 消息网关获取登录信息失败，第 {attempt}/{max_attempts} 次重试: {exc}")
                if attempt < max_attempts:
                    await asyncio.sleep(1.0)

        if last_error is not None:
            self._logger.error(f"Milky 消息网关未能完成路由激活，连接将保持只接收状态: {last_error}")

    async def handle_transport_disconnected(self) -> None:
        """处理传输层断开事件。"""
        runtime = self._require_runtime()
        self.reset_caches()
        await runtime.runtime_state.report_disconnected()

    async def handle_heartbeat_timeout(self, self_id: str) -> None:
        """Milky 不使用心跳监测，此方法保留但不执行任何操作。"""
        pass

    def _require_runtime(self) -> MilkyRuntimeBundle:
        runtime = self._runtime
        if runtime is None:
            raise RuntimeError("Milky 运行时尚未初始化")
        return runtime

    @staticmethod
    def _build_route_metadata(self_id: str, connection_id: str) -> Dict[str, Any]:
        route_metadata: Dict[str, Any] = {}
        if self_id:
            route_metadata["self_id"] = self_id
        if connection_id:
            route_metadata["connection_id"] = connection_id
        return route_metadata

    @staticmethod
    def _extract_self_id_from_login_response(response: Optional[Dict[str, Any]]) -> str:
        if not isinstance(response, Mapping):
            raise ValueError("get_login_info 响应缺少有效数据")

        self_id = str(response.get("uin") or response.get("user_id") or "").strip()
        if not self_id:
            raise ValueError("get_login_info 响应缺少有效的 uin")
        return self_id
