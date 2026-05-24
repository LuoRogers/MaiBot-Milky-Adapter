"""Milky 系统 API 端点。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from maibot_sdk import API

from .support import MilkyApiIdInput, MilkyApiSupportMixin


class MilkySystemApiMixin(MilkyApiSupportMixin):
    """Milky 系统信息 API。"""

    @API("adapter.milky.system.get_impl_info", description="获取协议端信息", version="1", public=True)
    async def api_get_impl_info(self) -> Optional[Dict[str, Any]]:
        return await self._call_milky_action_data("get_impl_info", {})

    @API("adapter.milky.system.get_user_profile", description="获取用户个人信息", version="1", public=True)
    async def api_get_user_profile(self, user_id: MilkyApiIdInput) -> Optional[Dict[str, Any]]:
        return await self._call_milky_action_data(
            "get_user_profile",
            {"user_id": self._normalize_positive_int(user_id, "user_id")},
        )

    @API("adapter.milky.system.set_avatar", description="设置头像", version="1", public=True)
    async def api_set_avatar(self, uri: str) -> Dict[str, Any]:
        return await self._call_milky_action(
            "set_avatar",
            {"uri": self._normalize_non_empty_string(uri, "uri")},
        )
