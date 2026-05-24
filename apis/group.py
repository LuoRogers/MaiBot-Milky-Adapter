"""Milky 群组 API 端点。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from maibot_sdk import API

from .support import MilkyApiIdInput, MilkyApiSupportMixin


class MilkyGroupApiMixin(MilkyApiSupportMixin):
    """Milky 群组管理 API。"""

    @API("adapter.milky.group.get_group_info", description="获取群信息", version="1", public=True)
    async def api_get_group_info(self, group_id: MilkyApiIdInput) -> Optional[Dict[str, Any]]:
        return await self._require_query_service().get_group_info(
            str(self._normalize_positive_int(group_id, "group_id"))
        )

    @API("adapter.milky.group.get_group_list", description="获取群列表", version="1", public=True)
    async def api_get_group_list(self, no_cache: bool = False) -> Optional[list]:
        return await self._require_query_service().get_group_list(no_cache=no_cache)

    @API("adapter.milky.group.get_group_member_info", description="获取群成员信息", version="1", public=True)
    async def api_get_group_member_info(
        self,
        group_id: MilkyApiIdInput,
        user_id: MilkyApiIdInput,
        no_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        return await self._require_query_service().get_group_member_info(
            str(self._normalize_positive_int(group_id, "group_id")),
            str(self._normalize_positive_int(user_id, "user_id")),
            no_cache=no_cache,
        )

    @API("adapter.milky.group.get_group_member_list", description="获取群成员列表", version="1", public=True)
    async def api_get_group_member_list(
        self,
        group_id: MilkyApiIdInput,
        no_cache: bool = False,
    ) -> Optional[list]:
        return await self._require_query_service().get_group_member_list(
            str(self._normalize_positive_int(group_id, "group_id")),
            no_cache=no_cache,
        )

    @API("adapter.milky.group.set_group_name", description="设置群名称", version="1", public=True)
    async def api_set_group_name(self, group_id: MilkyApiIdInput, group_name: str) -> Dict[str, Any]:
        return await self._require_query_service().set_group_name(
            self._normalize_positive_int(group_id, "group_id"),
            self._normalize_non_empty_string(group_name, "group_name"),
        )

    @API("adapter.milky.group.set_group_member_card", description="设置群名片", version="1", public=True)
    async def api_set_group_member_card(
        self,
        group_id: MilkyApiIdInput,
        user_id: MilkyApiIdInput,
        card: str,
    ) -> Dict[str, Any]:
        return await self._require_query_service().set_group_member_card(
            self._normalize_positive_int(group_id, "group_id"),
            self._normalize_positive_int(user_id, "user_id"),
            card,
        )

    @API("adapter.milky.group.set_group_member_mute", description="设置群成员禁言", version="1", public=True)
    async def api_set_group_member_mute(
        self,
        group_id: MilkyApiIdInput,
        user_id: MilkyApiIdInput,
        duration: int = 0,
    ) -> Dict[str, Any]:
        return await self._require_query_service().set_group_ban(
            self._normalize_positive_int(group_id, "group_id"),
            self._normalize_positive_int(user_id, "user_id"),
            self._normalize_non_negative_int(duration, "duration"),
        )

    @API("adapter.milky.group.set_group_whole_mute", description="设置群全体禁言", version="1", public=True)
    async def api_set_group_whole_mute(
        self,
        group_id: MilkyApiIdInput,
        is_mute: bool = True,
    ) -> Dict[str, Any]:
        return await self._require_query_service().set_group_whole_ban(
            self._normalize_positive_int(group_id, "group_id"),
            is_mute,
        )

    @API("adapter.milky.group.kick_group_member", description="踢出群成员", version="1", public=True)
    async def api_kick_group_member(
        self,
        group_id: MilkyApiIdInput,
        user_id: MilkyApiIdInput,
        reject_add_request: bool = False,
    ) -> Dict[str, Any]:
        return await self._require_query_service().set_group_kick(
            self._normalize_positive_int(group_id, "group_id"),
            self._normalize_positive_int(user_id, "user_id"),
            reject_add_request,
        )

    @API("adapter.milky.group.send_group_nudge", description="发送群戳一戳", version="1", public=True)
    async def api_send_group_nudge(
        self,
        group_id: MilkyApiIdInput,
        user_id: MilkyApiIdInput,
    ) -> Dict[str, Any]:
        return await self._call_milky_action(
            "send_group_nudge",
            {
                "group_id": self._normalize_positive_int(group_id, "group_id"),
                "user_id": self._normalize_positive_int(user_id, "user_id"),
            },
        )

    @API("adapter.milky.group.recall_group_message", description="撤回群消息", version="1", public=True)
    async def api_recall_group_message(
        self,
        group_id: MilkyApiIdInput,
        message_seq: MilkyApiIdInput,
    ) -> Dict[str, Any]:
        return await self._call_milky_action(
            "recall_group_message",
            {
                "group_id": self._normalize_positive_int(group_id, "group_id"),
                "message_seq": self._normalize_positive_int(message_seq, "message_seq"),
            },
        )

    @API("adapter.milky.group.quit_group", description="退出群", version="1", public=True)
    async def api_quit_group(self, group_id: MilkyApiIdInput) -> Dict[str, Any]:
        return await self._call_milky_action(
            "quit_group",
            {"group_id": self._normalize_positive_int(group_id, "group_id")},
        )
