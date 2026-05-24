"""Milky 通知事件编解码器。"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

import time

from ...services import MilkyQueryService
from ...types import MilkyPayload, MilkyPayloadDict


class MilkyNoticeCodec:
    """Milky QQ 通知事件编码器。"""

    def __init__(self, logger: Any, query_service: MilkyQueryService) -> None:
        self._logger = logger
        self._query_service = query_service

    async def build_notice_message_dict(self, event_type: str, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        """将 Milky 事件转换为 Host 可接受的消息字典。

        Args:
            event_type: Milky 事件类型。
            event_data: Milky 事件的 data 部分。
        """
        if event_type == "message_recall":
            return await self._build_recall_notice(event_data)
        if event_type == "friend_request":
            return await self._build_friend_request_notice(event_data)
        if event_type == "group_join_request":
            return await self._build_group_join_request_notice(event_data)
        if event_type == "group_invited_join_request":
            return await self._build_group_invited_join_request_notice(event_data)
        if event_type == "group_invitation":
            return await self._build_group_invitation_notice(event_data)
        if event_type == "friend_nudge":
            return await self._build_friend_nudge_notice(event_data)
        if event_type == "group_nudge":
            return await self._build_group_nudge_notice(event_data)
        if event_type == "group_member_increase":
            return await self._build_group_member_increase_notice(event_data)
        if event_type == "group_member_decrease":
            return await self._build_group_member_decrease_notice(event_data)
        if event_type == "group_mute":
            return await self._build_group_mute_notice(event_data)
        if event_type == "group_whole_mute":
            return await self._build_group_whole_mute_notice(event_data)
        if event_type == "group_admin_change":
            return await self._build_group_admin_change_notice(event_data)
        if event_type == "group_name_change":
            return await self._build_group_name_change_notice(event_data)
        if event_type == "group_message_reaction":
            return await self._build_group_message_reaction_notice(event_data)
        if event_type == "group_essence_message_change":
            return await self._build_group_essence_message_change_notice(event_data)
        if event_type == "bot_offline":
            return await self._build_bot_offline_notice(event_data)
        return None

    def build_notice_dedupe_key(self, event_type: str, event_data: MilkyPayload) -> Optional[str]:
        parts = [event_type]
        for key in ("message_seq", "notification_seq", "invitation_seq", "user_id", "group_id", "sender_id"):
            val = event_data.get(key)
            if val is not None:
                parts.append(f"{key}={val}")
        return ":".join(parts) if len(parts) > 1 else None

    async def _build_notice_base(
        self,
        event_data: MilkyPayload,
        notice_text: str,
        event_type: str,
        group_id: str = "",
        user_id: str = "",
    ) -> MilkyPayloadDict:
        timestamp_seconds = event_data.get("time", time.time())

        user_info: Dict[str, Any] = {
            "user_id": user_id or "",
            "user_nickname": user_id or "系统",
            "user_cardname": None,
        }

        if group_id:
            group_info_raw = event_data.get("group", {})
            if isinstance(group_info_raw, dict):
                user_info["user_nickname"] = str(
                    group_info_raw.get("nickname") or user_id or "系统"
                )
            group_info: Optional[Dict[str, Any]] = {
                "group_id": group_id,
                "group_name": str(group_info_raw.get("group_name") or f"group_{group_id}")
                if isinstance(group_info_raw, dict)
                else f"group_{group_id}",
            }
        else:
            group_info = None

        additional_config: Dict[str, Any] = {
            "milky_notice_type": event_type,
            "milky_notice_data": dict(event_data),
        }
        if group_id:
            additional_config["platform_io_target_group_id"] = group_id
        elif user_id:
            additional_config["platform_io_target_user_id"] = user_id

        message_info: Dict[str, Any] = {"user_info": user_info, "additional_config": additional_config}
        if group_info is not None:
            message_info["group_info"] = group_info

        return {
            "message_id": f"milky-notice-{event_type}-{uuid4().hex}",
            "timestamp": str(float(timestamp_seconds)),
            "platform": "qq",
            "message_info": message_info,
            "raw_message": [{"type": "text", "data": notice_text}],
            "is_mentioned": False,
            "is_at": False,
            "is_emoji": False,
            "is_picture": False,
            "is_command": False,
            "is_notify": True,
            "session_id": "",
            "processed_plain_text": notice_text,
            "display_message": notice_text,
        }

    async def _build_recall_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        message_scene = str(event_data.get("message_scene") or "").strip()
        peer_id = str(event_data.get("peer_id") or "").strip()
        sender_id = str(event_data.get("sender_id") or "").strip()
        display_suffix = str(event_data.get("display_suffix") or "").strip()
        group_id = peer_id if message_scene == "group" else ""
        user_id = sender_id
        notice_text = f"{sender_id} 撤回了一条消息"
        if display_suffix:
            notice_text += f" ({display_suffix})"
        return await self._build_notice_base(event_data, notice_text, "message_recall", group_id, user_id)

    async def _build_friend_request_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        initiator_id = str(event_data.get("initiator_id") or "").strip()
        comment = str(event_data.get("comment") or "").strip()
        notice_text = f"收到来自 {initiator_id} 的好友请求"
        if comment:
            notice_text += f"：{comment}"
        return await self._build_notice_base(event_data, notice_text, "friend_request", "", initiator_id)

    async def _build_group_join_request_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        initiator_id = str(event_data.get("initiator_id") or "").strip()
        comment = str(event_data.get("comment") or "").strip()
        notice_text = f"用户 {initiator_id} 申请加入群 {group_id}"
        if comment:
            notice_text += f"：{comment}"
        return await self._build_notice_base(event_data, notice_text, "group_join_request", group_id, initiator_id)

    async def _build_group_invited_join_request_notice(
        self, event_data: MilkyPayload
    ) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        initiator_id = str(event_data.get("initiator_id") or "").strip()
        target_user_id = str(event_data.get("target_user_id") or "").strip()
        notice_text = f"用户 {initiator_id} 邀请 {target_user_id} 加入群 {group_id}"
        return await self._build_notice_base(
            event_data, notice_text, "group_invited_join_request", group_id, initiator_id
        )

    async def _build_group_invitation_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        initiator_id = str(event_data.get("initiator_id") or "").strip()
        notice_text = f"收到来自 {initiator_id} 的入群邀请（群 {group_id}）"
        return await self._build_notice_base(event_data, notice_text, "group_invitation", group_id, initiator_id)

    async def _build_friend_nudge_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        user_id = str(event_data.get("user_id") or "").strip()
        display_action = str(event_data.get("display_action") or "").strip()
        display_suffix = str(event_data.get("display_suffix") or "").strip()
        notice_text = display_action or f"收到来自 {user_id} 的戳一戳"
        if display_suffix:
            notice_text += f" {display_suffix}"
        return await self._build_notice_base(event_data, notice_text, "friend_nudge", "", user_id)

    async def _build_group_nudge_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        sender_id = str(event_data.get("sender_id") or "").strip()
        receiver_id = str(event_data.get("receiver_id") or "").strip()
        display_action = str(event_data.get("display_action") or "").strip()
        notice_text = display_action or f"{sender_id} 戳了戳 {receiver_id}"
        return await self._build_notice_base(event_data, notice_text, "group_nudge", group_id, sender_id)

    async def _build_group_member_increase_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        user_id = str(event_data.get("user_id") or "").strip()
        notice_text = f"用户 {user_id} 加入了群聊"
        return await self._build_notice_base(event_data, notice_text, "group_member_increase", group_id, user_id)

    async def _build_group_member_decrease_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        user_id = str(event_data.get("user_id") or "").strip()
        operator_id = str(event_data.get("operator_id") or "").strip()
        if operator_id:
            notice_text = f"用户 {user_id} 被管理员 {operator_id} 移出群聊"
        else:
            notice_text = f"用户 {user_id} 离开了群聊"
        return await self._build_notice_base(event_data, notice_text, "group_member_decrease", group_id, user_id)

    async def _build_group_mute_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        user_id = str(event_data.get("user_id") or "").strip()
        operator_id = str(event_data.get("operator_id") or "").strip()
        duration = event_data.get("duration", 0)
        if duration == 0:
            notice_text = f"管理员 {operator_id} 解除了用户 {user_id} 的禁言"
        else:
            notice_text = f"管理员 {operator_id} 禁言了用户 {user_id}，时长 {duration} 秒"
        return await self._build_notice_base(event_data, notice_text, "group_mute", group_id, operator_id)

    async def _build_group_whole_mute_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        operator_id = str(event_data.get("operator_id") or "").strip()
        is_mute = event_data.get("is_mute", True)
        if is_mute:
            notice_text = f"管理员 {operator_id} 开启了全体禁言"
        else:
            notice_text = f"管理员 {operator_id} 解除了全体禁言"
        return await self._build_notice_base(event_data, notice_text, "group_whole_mute", group_id, operator_id)

    async def _build_group_admin_change_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        user_id = str(event_data.get("user_id") or "").strip()
        is_set = event_data.get("is_set", True)
        if is_set:
            notice_text = f"用户 {user_id} 被设置为管理员"
        else:
            notice_text = f"用户 {user_id} 被取消管理员"
        return await self._build_notice_base(event_data, notice_text, "group_admin_change", group_id, user_id)

    async def _build_group_name_change_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        new_group_name = str(event_data.get("new_group_name") or "").strip()
        operator_id = str(event_data.get("operator_id") or "").strip()
        notice_text = f"管理员 {operator_id} 修改了群名称为：{new_group_name}"
        return await self._build_notice_base(event_data, notice_text, "group_name_change", group_id, operator_id)

    async def _build_group_message_reaction_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        user_id = str(event_data.get("user_id") or "").strip()
        is_add = event_data.get("is_add", True)
        if is_add:
            notice_text = f"用户 {user_id} 给消息添加了表情回应"
        else:
            notice_text = f"用户 {user_id} 移除了消息表情回应"
        return await self._build_notice_base(event_data, notice_text, "group_message_reaction", group_id, user_id)

    async def _build_group_essence_message_change_notice(
        self, event_data: MilkyPayload
    ) -> Optional[MilkyPayloadDict]:
        group_id = str(event_data.get("group_id") or "").strip()
        is_set = event_data.get("is_set", True)
        if is_set:
            notice_text = "一条消息被设为精华消息"
        else:
            notice_text = "一条消息被取消精华"
        return await self._build_notice_base(event_data, notice_text, "group_essence_message_change", group_id)

    async def _build_bot_offline_notice(self, event_data: MilkyPayload) -> Optional[MilkyPayloadDict]:
        reason = str(event_data.get("reason") or "").strip()
        notice_text = f"机器人已离线"
        if reason:
            notice_text += f"：{reason}"
        return await self._build_notice_base(event_data, notice_text, "bot_offline")
