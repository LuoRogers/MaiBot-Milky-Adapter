"""Milky 运行时组件容器。"""

from __future__ import annotations

from dataclasses import dataclass

from ..codecs.inbound import MilkyInboundCodec
from ..codecs.notice import MilkyNoticeCodec
from ..codecs.outbound import MilkyOutboundCodec
from ..filters import MilkyChatFilter, MilkyRegexFilter
from ..heartbeat_monitor import MilkyHeartbeatMonitor
from ..runtime_state import MilkyRuntimeStateManager
from ..services import MilkyActionService, MilkyQueryService
from ..transport import MilkyTransportClient


@dataclass
class MilkyRuntimeBundle:
    """Milky 运行时依赖集合。"""

    action_service: MilkyActionService
    chat_filter: MilkyChatFilter
    heartbeat_monitor: MilkyHeartbeatMonitor
    inbound_codec: MilkyInboundCodec
    notice_codec: MilkyNoticeCodec
    outbound_codec: MilkyOutboundCodec
    query_service: MilkyQueryService
    runtime_state: MilkyRuntimeStateManager
    regex_filter: MilkyRegexFilter
    transport: MilkyTransportClient
