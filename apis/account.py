"""Milky 账号 API 端点。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from maibot_sdk import API

from .support import MilkyApiIdInput, MilkyApiSupportMixin


class MilkyAccountApiMixin(MilkyApiSupportMixin):
    """Milky 账号与好友相关 API。"""

    @API("adapter.milky.account.get_login_info", description="获取登录信息", version="1", public=True)
    async def api_get_login_info(self) -> Optional[Dict[str, Any]]:
        return await self._require_query_service().get_login_info()

    @API("adapter.milky.account.get_stranger_info", description="获取用户信息", version="1", public=True)
    async def api_get_stranger_info(self, user_id: MilkyApiIdInput) -> Optional[Dict[str, Any]]:
        return await self._require_query_service().get_stranger_info(
            str(self._normalize_positive_int(user_id, "user_id"))
        )

    @API("adapter.milky.account.get_friend_list", description="获取好友列表", version="1", public=True)
    async def api_get_friend_list(self, no_cache: bool = False) -> Optional[list]:
        return await self._require_query_service().get_friend_list(no_cache=no_cache)

    @API("adapter.milky.account.set_nickname", description="设置昵称", version="1", public=True)
    async def api_set_nickname(self, nickname: str) -> Dict[str, Any]:
        return await self._require_query_service().set_nickname(
            self._normalize_non_empty_string(nickname, "nickname")
        )

    @API("adapter.milky.account.set_bio", description="设置个性签名", version="1", public=True)
    async def api_set_bio(self, bio: str) -> Dict[str, Any]:
        return await self._require_query_service().set_bio(bio)

    @API("adapter.milky.account.send_poke", description="发送戳一戳", version="1", public=True)
    async def api_send_poke(
        self,
        user_id: MilkyApiIdInput,
        group_id: Optional[MilkyApiIdInput] = None,
    ) -> Dict[str, Any]:
        normalized_user_id = self._normalize_positive_int(user_id, "user_id")
        normalized_group_id = None
        if group_id is not None and str(group_id).strip():
            normalized_group_id = self._normalize_positive_int(group_id, "group_id")
        return await self._require_query_service().send_poke(
            user_id=normalized_user_id,
            group_id=normalized_group_id,
        )

    @API("adapter.milky.account.send_friend_nudge", description="发送好友戳一戳", version="1", public=True)
    async def api_send_friend_nudge(
        self,
        user_id: MilkyApiIdInput,
        is_self: bool = False,
    ) -> Dict[str, Any]:
        return await self._call_milky_action(
            "send_friend_nudge",
            {"user_id": self._normalize_positive_int(user_id, "user_id"), "is_self": is_self},
        )
