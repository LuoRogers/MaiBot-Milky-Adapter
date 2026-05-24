"""Milky 入站消息编解码。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple
from uuid import uuid4

import base64
import hashlib
import time

from ...services import MilkyQueryService
from ...types import MilkyIncomingSegment, MilkyIncomingSegments, MilkyPayload, MilkySegment, MilkySegments


class MilkyInboundCodec:
    """Milky 入站消息编码器。"""

    def __init__(self, logger: Any, query_service: MilkyQueryService) -> None:
        self._logger = logger
        self._query_service = query_service

    async def build_message_dict(
        self,
        event_data: MilkyPayload,
        self_id: str,
    ) -> Dict[str, Any]:
        """构造 Host 侧可接受的 ``MessageDict``。

        Args:
            event_data: Milky message_receive 事件的 data 部分。
            self_id: 当前机器人账号 ID。
        """
        message_scene = str(event_data.get("message_scene") or "").strip() or "friend"
        peer_id = str(event_data.get("peer_id") or "").strip()
        sender_id = str(event_data.get("sender_id") or "").strip()
        message_seq = event_data.get("message_seq")
        segments = event_data.get("segments", [])

        if message_scene == "group":
            group_info_raw = event_data.get("group", {})
            group_member_raw = event_data.get("group_member", {})
            group_id = str(group_info_raw.get("group_id") or peer_id).strip()
            group_name = str(group_info_raw.get("group_name") or f"group_{group_id}").strip()
            user_nickname = str(group_member_raw.get("card") or group_member_raw.get("nickname") or sender_id).strip()
            user_cardname = str(group_member_raw.get("card") or "").strip() or None
        elif message_scene == "friend":
            friend_info_raw = event_data.get("friend", {})
            group_id = ""
            group_name = ""
            user_nickname = str(friend_info_raw.get("nickname") or sender_id).strip()
            user_cardname = None
        else:
            group_info_raw = event_data.get("group", {})
            group_id = str(group_info_raw.get("group_id") or "").strip()
            group_name = str(group_info_raw.get("group_name") or "").strip()
            user_nickname = sender_id
            user_cardname = None

        # 使用异步版本以下载图片等资源
        raw_message, is_at = await self._convert_segments(segments, self_id)
        if not raw_message:
            raw_message = [self._build_text_segment("[unsupported]")]

        plain_text = self.build_plain_text(raw_message)

        timestamp_seconds = event_data.get("time")
        if not isinstance(timestamp_seconds, (int, float)):
            timestamp_seconds = time.time()

        additional_config: Dict[str, Any] = {
            "self_id": self_id,
            "milky_message_scene": message_scene,
            "milky_message_seq": message_seq,
        }
        if group_id:
            additional_config["platform_io_target_group_id"] = group_id
        else:
            additional_config["platform_io_target_user_id"] = sender_id

        message_info: Dict[str, Any] = {
            "user_info": {
                "user_id": sender_id,
                "user_nickname": user_nickname,
                "user_cardname": user_cardname,
            },
            "additional_config": additional_config,
        }
        if group_id:
            message_info["group_info"] = {"group_id": group_id, "group_name": group_name}

        message_id = f"milky-{message_scene}-{peer_id}-{message_seq}" if message_seq else f"milky-{uuid4().hex}"

        return {
            "message_id": message_id,
            "timestamp": str(float(timestamp_seconds)),
            "platform": "qq",
            "message_info": message_info,
            "raw_message": raw_message,
            "is_mentioned": is_at,
            "is_at": is_at,
            "is_emoji": False,
            "is_picture": False,
            "is_command": plain_text.startswith("/"),
            "is_notify": False,
            "session_id": "",
            "processed_plain_text": plain_text,
            "display_message": plain_text,
        }

    async def _convert_segments(self, segments: Any, self_id: str) -> Tuple[MilkySegments, bool]:
        """转换消息段列表。"""
        if not isinstance(segments, list):
            return [], False
        return await self._convert_incoming_segments(segments, self_id)

    async def _convert_incoming_segments(
        self,
        segments: List[Any],
        self_id: str,
    ) -> Tuple[MilkySegments, bool]:
        """将 Milky 消息段转换为 Host 消息段结构。"""
        converted_segments: MilkySegments = []
        is_at = False

        for segment in segments:
            if not isinstance(segment, Mapping):
                continue

            segment_type = str(segment.get("type") or "").strip()
            segment_data = segment.get("data", {})
            if not isinstance(segment_data, Mapping):
                segment_data = {}

            if segment_type == "text":
                text_value = str(segment_data.get("text") or "")
                if text_value:
                    converted_segments.append(self._build_text_segment(text_value))
                continue

            if segment_type == "mention":
                target_user_id = str(segment_data.get("user_id") or "").strip()
                target_name = str(segment_data.get("name") or "").strip()
                if target_user_id:
                    converted_segments.append({
                        "type": "at",
                        "data": {
                            "target_user_id": target_user_id,
                            "target_user_nickname": target_name or None,
                            "target_user_cardname": None,
                        },
                    })
                    if self_id and target_user_id == self_id:
                        is_at = True
                continue

            if segment_type == "mention_all":
                converted_segments.append({
                    "type": "at",
                    "data": {
                        "target_user_id": "all",
                        "target_user_nickname": "全体成员",
                        "target_user_cardname": None,
                    },
                })
                continue

            if segment_type == "face":
                face_id = str(segment_data.get("face_id") or "").strip()
                is_large = segment_data.get("is_large", False)
                if is_large:
                    converted_segments.append(self._build_text_segment("[超级表情]"))
                elif face_id:
                    converted_segments.append(self._build_text_segment(f"[表情:{face_id}]"))
                continue

            if segment_type == "reply":
                reply_seq = segment_data.get("message_seq")
                sender_id = str(segment_data.get("sender_id") or "").strip()
                if reply_seq is not None:
                    reply_payload: Dict[str, Any] = {"target_message_id": str(reply_seq)}
                    if sender_id:
                        reply_payload["target_message_sender_id"] = sender_id
                    sender_name = str(segment_data.get("sender_name") or "").strip()
                    if sender_name:
                        reply_payload["target_message_sender_nickname"] = sender_name

                    # 提取被引用的原消息内容（Milky 协议 1.2+ 支持）
                    quoted_segments = segment_data.get("segments")
                    if isinstance(quoted_segments, list) and quoted_segments:
                        quoted_content, _ = await self._convert_segments(quoted_segments, self_id)
                        if quoted_content:
                            reply_payload["target_message_content"] = self.build_plain_text(quoted_content)

                    converted_segments.append({"type": "reply", "data": reply_payload})
                continue

            if segment_type == "image":
                resource_id = str(segment_data.get("resource_id") or "").strip()
                temp_url = str(segment_data.get("temp_url") or "").strip()
                sub_type = str(segment_data.get("sub_type") or "normal").strip()
                if sub_type == "sticker":
                    converted_segments.append(await self._build_image_segment("emoji", resource_id, temp_url))
                else:
                    converted_segments.append(await self._build_image_segment("image", resource_id, temp_url))
                continue

            if segment_type == "record":
                resource_id = str(segment_data.get("resource_id") or "").strip()
                temp_url = str(segment_data.get("temp_url") or "").strip()
                converted_segments.append(await self._build_image_segment("voice", resource_id, temp_url))
                continue

            if segment_type == "video":
                resource_id = str(segment_data.get("resource_id") or "").strip()
                temp_url = str(segment_data.get("temp_url") or "").strip()
                converted_segments.append(await self._build_image_segment("video", resource_id, temp_url))
                continue

            if segment_type == "file":
                file_name = str(segment_data.get("file_name") or "").strip()
                file_size = segment_data.get("file_size", 0)
                file_text = f"[文件] {file_name}" if file_name else "[文件]"
                if file_size:
                    file_text += f" (大小: {file_size})"
                converted_segments.append(self._build_text_segment(file_text))
                continue

            if segment_type == "forward":
                forward_id = str(segment_data.get("forward_id") or "").strip()
                if forward_id:
                    converted_segments.append({"type": "forward", "data": {"forward_id": forward_id}})
                continue

            if segment_type == "market_face":
                summary = str(segment_data.get("summary") or "[商城表情]").strip()
                url = str(segment_data.get("url") or "").strip()
                if url:
                    converted_segments.append(await self._build_image_segment("emoji", "", url))
                else:
                    converted_segments.append(self._build_text_segment(summary))
                continue

            if segment_type in ("light_app", "xml"):
                converted_segments.append(self._build_text_segment(f"[{segment_type}]"))
                continue

        return converted_segments, is_at

    async def _build_image_segment(
        self,
        seg_type: str,
        resource_id: str,
        temp_url: str,
    ) -> MilkySegment:
        """构造媒体消息段，尝试获取实际数据。"""
        url_to_download = temp_url

        # 如果没有 temp_url 但有 resource_id，尝试获取临时链接
        if not url_to_download and resource_id:
            try:
                url_to_download = await self._query_service.get_resource_temp_url(resource_id) or ""
            except Exception:
                pass

        # 如果有 URL，尝试下载
        if url_to_download:
            binary_data = await self._query_service.download_binary(url_to_download)
            if binary_data:
                return {
                    "type": seg_type,
                    "data": "",
                    "hash": hashlib.sha256(binary_data).hexdigest(),
                    "binary_data_base64": base64.b64encode(binary_data).decode("ascii"),
                }

        # 下载失败，返回占位文本
        return self._build_text_segment(f"[{seg_type}]")

    @staticmethod
    def _build_text_segment(text: str) -> MilkySegment:
        return {"type": "text", "data": text}

    @staticmethod
    def build_plain_text(segments: MilkySegments) -> str:
        parts = []
        for seg in segments:
            if seg.get("type") == "text":
                parts.append(str(seg.get("data") or ""))
            elif seg.get("type") == "at":
                at_data = seg.get("data", {})
                if isinstance(at_data, Mapping):
                    target_name = str(at_data.get("target_user_nickname") or at_data.get("target_user_id") or "")
                    parts.append(f"@{target_name}")
        return "".join(parts).strip()
