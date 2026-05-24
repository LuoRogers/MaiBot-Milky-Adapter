"""Milky QQ 平台查询服务。"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional

from ..types import MilkyActionParams, MilkyActionResponse, MilkyPayloadDict, MilkyPayloadList
from .action_service import MilkyActionService


class MilkyQueryService:
    """Milky QQ 平台查询与管理动作服务。"""

    def __init__(self, action_service: MilkyActionService, logger: Any) -> None:
        self._action_service = action_service
        self._logger = logger

    async def call_action(self, action_name: str, params: MilkyActionParams) -> MilkyActionResponse:
        return await self._action_service.call_action(action_name, params)

    async def call_action_data(self, action_name: str, params: MilkyActionParams) -> Any:
        return await self._action_service.call_action_data(action_name, params)

    async def get_login_info(self) -> Optional[MilkyPayloadDict]:
        response_data = await self._safe_call_action_data("get_login_info", {})
        return response_data if isinstance(response_data, dict) else None

    async def get_stranger_info(self, user_id: str, no_cache: bool = False) -> Optional[MilkyPayloadDict]:
        response_data = await self._safe_call_action_data(
            "get_user_profile",
            {"user_id": int(user_id)},
        )
        return response_data if isinstance(response_data, dict) else None

    async def get_friend_list(self, no_cache: bool = False) -> Optional[MilkyPayloadList]:
        response_data = await self._safe_call_action_data("get_friend_list", {"no_cache": bool(no_cache)})
        if isinstance(response_data, dict):
            friends = response_data.get("friends")
            if isinstance(friends, list):
                return friends
        return None

    async def get_group_info(self, group_id: str) -> Optional[MilkyPayloadDict]:
        response_data = await self._safe_call_action_data("get_group_info", {"group_id": int(group_id)})
        if isinstance(response_data, dict):
            group = response_data.get("group")
            if isinstance(group, dict):
                return group
        return response_data if isinstance(response_data, dict) else None

    async def get_group_list(self, no_cache: bool = False) -> Optional[MilkyPayloadList]:
        response_data = await self._safe_call_action_data("get_group_list", {"no_cache": bool(no_cache)})
        if isinstance(response_data, dict):
            groups = response_data.get("groups")
            if isinstance(groups, list):
                return groups
        return None

    async def get_group_member_info(
        self,
        group_id: str,
        user_id: str,
        no_cache: bool = True,
    ) -> Optional[MilkyPayloadDict]:
        response_data = await self._safe_call_action_data(
            "get_group_member_info",
            {"group_id": int(group_id), "user_id": int(user_id), "no_cache": bool(no_cache)},
        )
        if isinstance(response_data, dict):
            member = response_data.get("member")
            if isinstance(member, dict):
                return member
        return response_data if isinstance(response_data, dict) else None

    async def get_group_member_list(self, group_id: str, no_cache: bool = False) -> Optional[MilkyPayloadList]:
        response_data = await self._safe_call_action_data(
            "get_group_member_list",
            {"group_id": int(group_id), "no_cache": bool(no_cache)},
        )
        if isinstance(response_data, dict):
            members = response_data.get("members")
            if isinstance(members, list):
                return members
        return None

    async def get_message_detail(
        self,
        message_scene: str,
        peer_id: str,
        message_seq: int,
    ) -> Optional[MilkyPayloadDict]:
        response_data = await self._safe_call_action_data(
            "get_message",
            {"message_scene": message_scene, "peer_id": int(peer_id), "message_seq": message_seq},
        )
        if isinstance(response_data, dict):
            message = response_data.get("message")
            if isinstance(message, dict):
                return message
        return response_data if isinstance(response_data, dict) else None

    async def get_resource_temp_url(self, resource_id: str) -> Optional[str]:
        response_data = await self._safe_call_action_data(
            "get_resource_temp_url",
            {"resource_id": resource_id},
        )
        if isinstance(response_data, dict):
            return str(response_data.get("url") or "").strip() or None
        return None

    async def set_group_ban(self, group_id: int, user_id: int, duration: int) -> MilkyActionResponse:
        return await self.call_action(
            "set_group_member_mute",
            {"group_id": group_id, "user_id": user_id, "duration": duration},
        )

    async def set_group_whole_ban(self, group_id: int, enable: bool) -> MilkyActionResponse:
        return await self.call_action(
            "set_group_whole_mute",
            {"group_id": group_id, "is_mute": enable},
        )

    async def set_group_kick(
        self,
        group_id: int,
        user_id: int,
        reject_add_request: bool = False,
    ) -> MilkyActionResponse:
        return await self.call_action(
            "kick_group_member",
            {"group_id": group_id, "user_id": user_id, "reject_add_request": reject_add_request},
        )

    async def send_poke(
        self,
        user_id: int,
        group_id: Optional[int] = None,
    ) -> MilkyActionResponse:
        if group_id is not None:
            return await self.call_action("send_group_nudge", {"group_id": group_id, "user_id": user_id})
        return await self.call_action("send_friend_nudge", {"user_id": user_id})

    async def recall_message(
        self,
        message_scene: str,
        peer_id: int,
        message_seq: int,
    ) -> MilkyActionResponse:
        if message_scene == "friend":
            return await self.call_action(
                "recall_private_message",
                {"user_id": peer_id, "message_seq": message_seq},
            )
        return await self.call_action(
            "recall_group_message",
            {"group_id": peer_id, "message_seq": message_seq},
        )

    async def set_group_name(self, group_id: int, group_name: str) -> MilkyActionResponse:
        return await self.call_action(
            "set_group_name",
            {"group_id": group_id, "new_group_name": group_name},
        )

    async def set_group_member_card(self, group_id: int, user_id: int, card: str) -> MilkyActionResponse:
        return await self.call_action(
            "set_group_member_card",
            {"group_id": group_id, "user_id": user_id, "card": card},
        )

    async def set_group_member_special_title(
        self, group_id: int, user_id: int, special_title: str
    ) -> MilkyActionResponse:
        return await self.call_action(
            "set_group_member_special_title",
            {"group_id": group_id, "user_id": user_id, "special_title": special_title},
        )

    async def set_nickname(self, new_nickname: str) -> MilkyActionResponse:
        return await self.call_action("set_nickname", {"new_nickname": new_nickname})

    async def set_bio(self, new_bio: str) -> MilkyActionResponse:
        return await self.call_action("set_bio", {"new_bio": new_bio})

    async def download_binary(self, url: str) -> Optional[bytes]:
        return await self._action_service.download_binary(url)

    async def _safe_call_action_data(self, action_name: str, params: MilkyActionParams) -> Any:
        return await self._action_service.safe_call_action_data(action_name, params)
