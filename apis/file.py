"""Milky 文件 API 端点。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from maibot_sdk import API

from .support import MilkyApiIdInput, MilkyApiSupportMixin


class MilkyFileApiMixin(MilkyApiSupportMixin):
    """Milky 文件管理 API。"""

    @API("adapter.milky.file.upload_private_file", description="上传私聊文件", version="1", public=True)
    async def api_upload_private_file(
        self,
        user_id: MilkyApiIdInput,
        file_uri: str,
        file_name: str,
    ) -> Dict[str, Any]:
        return await self._call_milky_action(
            "upload_private_file",
            {
                "user_id": self._normalize_positive_int(user_id, "user_id"),
                "file_uri": self._normalize_non_empty_string(file_uri, "file_uri"),
                "file_name": self._normalize_non_empty_string(file_name, "file_name"),
            },
        )

    @API("adapter.milky.file.upload_group_file", description="上传群文件", version="1", public=True)
    async def api_upload_group_file(
        self,
        group_id: MilkyApiIdInput,
        file_uri: str,
        file_name: str,
        parent_folder_id: str = "/",
    ) -> Dict[str, Any]:
        return await self._call_milky_action(
            "upload_group_file",
            {
                "group_id": self._normalize_positive_int(group_id, "group_id"),
                "file_uri": self._normalize_non_empty_string(file_uri, "file_uri"),
                "file_name": self._normalize_non_empty_string(file_name, "file_name"),
                "parent_folder_id": parent_folder_id,
            },
        )
