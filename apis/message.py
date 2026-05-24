"""Milky 消息 API 端点。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from maibot_sdk import API

from .support import MilkyApiIdInput, MilkyApiSupportMixin


class MilkyMessageApiMixin(MilkyApiSupportMixin):
    """Milky 消息相关 API。"""

    @API("adapter.milky.message.recall_private_message", description="撤回私聊消息", version="1", public=True)
    async def api_recall_private_message(
        self,
        user_id: MilkyApiIdInput,
        message_seq: MilkyApiIdInput,
    ) -> Dict[str, Any]:
        return await self._call_milky_action(
            "recall_private_message",
            {
                "user_id": self._normalize_positive_int(user_id, "user_id"),
                "message_seq": self._normalize_positive_int(message_seq, "message_seq"),
            },
        )

    @API("adapter.milky.message.get_resource_temp_url", description="获取资源临时链接", version="1", public=True)
    async def api_get_resource_temp_url(self, resource_id: str) -> Optional[str]:
        return await self._require_query_service().get_resource_temp_url(
            self._normalize_non_empty_string(resource_id, "resource_id")
        )

    @API("adapter.milky.message.mark_message_as_read", description="标记消息已读", version="1", public=True)
    async def api_mark_message_as_read(
        self,
        message_scene: str,
        peer_id: MilkyApiIdInput,
        message_seq: MilkyApiIdInput,
    ) -> Dict[str, Any]:
        normalized_scene = self._normalize_non_empty_string(message_scene, "message_scene")
        if normalized_scene not in ("friend", "group", "temp"):
            raise ValueError("message_scene 必须是 friend、group 或 temp")
        return await self._call_milky_action(
            "mark_message_as_read",
            {
                "message_scene": normalized_scene,
                "peer_id": self._normalize_positive_int(peer_id, "peer_id"),
                "message_seq": self._normalize_positive_int(message_seq, "message_seq"),
            },
        )
