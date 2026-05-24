"""Milky 运行时组件构建器。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Coroutine

from ..codecs.inbound import MilkyInboundCodec
from ..codecs.notice import MilkyNoticeCodec
from ..codecs.outbound import MilkyOutboundCodec
from ..filters import MilkyChatFilter, MilkyRegexFilter
from ..heartbeat_monitor import MilkyHeartbeatMonitor
from ..runtime_state import MilkyRuntimeStateManager
from ..services import MilkyActionService, MilkyQueryService
from ..transport import MilkyTransportClient
from .bundle import MilkyRuntimeBundle


class MilkyRuntimeBuilder:
    """按固定依赖图构建 Milky 运行时组件。"""

    def __init__(self, gateway_capability: Any, logger: Any, gateway_name: str) -> None:
        self._gateway_capability = gateway_capability
        self._logger = logger
        self._gateway_name = gateway_name

    def build(
        self,
        on_connection_opened: Callable[[], Coroutine[Any, Any, None]],
        on_connection_closed: Callable[[], Coroutine[Any, Any, None]],
        on_payload: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
        on_heartbeat_timeout: Callable[[str], Awaitable[None]],
    ) -> MilkyRuntimeBundle:
        chat_filter = MilkyChatFilter(self._logger)
        regex_filter = MilkyRegexFilter(self._logger)
        transport = MilkyTransportClient(
            logger=self._logger,
            on_connection_opened=on_connection_opened,
            on_connection_closed=on_connection_closed,
            on_payload=on_payload,
        )
        action_service = MilkyActionService(self._logger, transport)
        query_service = MilkyQueryService(action_service, self._logger)
        inbound_codec = MilkyInboundCodec(self._logger, query_service)
        notice_codec = MilkyNoticeCodec(self._logger, query_service)
        runtime_state = MilkyRuntimeStateManager(
            gateway_capability=self._gateway_capability,
            logger=self._logger,
            gateway_name=self._gateway_name,
        )
        heartbeat_monitor = MilkyHeartbeatMonitor(
            logger=self._logger,
            on_timeout=on_heartbeat_timeout,
        )
        outbound_codec = MilkyOutboundCodec()

        return MilkyRuntimeBundle(
            action_service=action_service,
            chat_filter=chat_filter,
            heartbeat_monitor=heartbeat_monitor,
            inbound_codec=inbound_codec,
            notice_codec=notice_codec,
            outbound_codec=outbound_codec,
            query_service=query_service,
            runtime_state=runtime_state,
            regex_filter=regex_filter,
            transport=transport,
        )
