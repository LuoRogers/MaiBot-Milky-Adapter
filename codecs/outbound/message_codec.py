"""Milky 出站消息编解码。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from .segment_encoder import MilkyOutboundSegmentEncoder


class MilkyOutboundCodec:
    """Milky 出站消息编码器。"""

    def __init__(self) -> None:
        self._segment_encoder = MilkyOutboundSegmentEncoder()

    def build_outbound_action(
        self,
        message: Mapping[str, Any],
        route: Mapping[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """为 Host 出站消息构造 Milky API 调用。

        Returns:
            Tuple[str, Dict[str, Any]]: API 名称与参数字典。
        """
        message_info = message.get("message_info", {})
        if not isinstance(message_info, Mapping):
            message_info = {}

        group_info = message_info.get("group_info", {})
        if not isinstance(group_info, Mapping):
            group_info = {}

        additional_config = message_info.get("additional_config", {})
        if not isinstance(additional_config, Mapping):
            additional_config = {}

        raw_message = message.get("raw_message", [])
        segments = self._segment_encoder.convert_segments(raw_message)

        if target_group_id := str(
            group_info.get("group_id") or additional_config.get("platform_io_target_group_id") or ""
        ).strip():
            return "send_group_message", {"group_id": int(target_group_id), "message": segments}

        target_user_id = str(
            additional_config.get("platform_io_target_user_id")
            or additional_config.get("target_user_id")
            or route.get("target_user_id")
            or ""
        ).strip()
        if not target_user_id:
            raise ValueError("Outbound private message is missing target_user_id")

        return "send_private_message", {"user_id": int(target_user_id), "message": segments}
