"""Milky 出站消息段编码器。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional


class MilkyOutboundSegmentEncoder:
    """将 Host 消息段转换为 Milky 消息段。"""

    def __init__(self) -> None:
        self._segment_builders: Dict[str, Callable[[Mapping[str, Any]], List[Dict[str, Any]]]] = {
            "at": self._build_at_segments,
            "emoji": self._build_emoji_segments,
            "face": self._build_face_segments,
            "file": self._build_file_segments,
            "forward": self._build_forward_segments,
            "image": self._build_image_segments,
            "reply": self._build_reply_segments,
            "text": self._build_text_segments,
            "video": self._build_video_segments,
            "voice": self._build_voice_segments,
        }

    def convert_segments(self, raw_message: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_message, list):
            return [{"type": "text", "data": {"text": ""}}]

        outbound_segments: List[Dict[str, Any]] = []
        for item in raw_message:
            if not isinstance(item, Mapping):
                continue

            item_type = str(item.get("type") or "").strip()
            segment_builder = self._segment_builders.get(item_type)
            if segment_builder is None:
                fallback_text = f"[unsupported:{item_type or 'unknown'}]"
                outbound_segments.append({"type": "text", "data": {"text": fallback_text}})
                continue

            built_segments = segment_builder(item)
            if built_segments:
                outbound_segments.extend(built_segments)
                continue

            fallback_text = f"[{item_type or 'unknown'}]"
            outbound_segments.append({"type": "text", "data": {"text": fallback_text}})

        if not outbound_segments:
            outbound_segments.append({"type": "text", "data": {"text": ""}})
        return outbound_segments

    def _build_text_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        text_value = str(item.get("data") or "")
        if not text_value:
            return []
        return [{"type": "text", "data": {"text": text_value}}]

    def _build_at_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        item_data = item.get("data")
        if not isinstance(item_data, Mapping):
            return []
        target_user_id = str(item_data.get("target_user_id") or "").strip()
        if not target_user_id:
            return []
        if target_user_id == "all":
            return [{"type": "mention_all", "data": {}}]
        try:
            user_id_int = int(target_user_id)
        except ValueError:
            return []
        return [{"type": "mention", "data": {"user_id": user_id_int}}]

    def _build_reply_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        item_data = item.get("data")
        if isinstance(item_data, Mapping):
            target_message_id = str(item_data.get("target_message_id") or "").strip()
        else:
            target_message_id = str(item_data or "").strip()
        if not target_message_id:
            return []

        # 处理 milky-{scene}-{peer_id}-{message_seq} 格式的消息 ID
        if target_message_id.startswith("milky-"):
            parts = target_message_id.split("-")
            if len(parts) >= 4:
                try:
                    message_seq = int(parts[-1])
                except ValueError:
                    return []
                return [{"type": "reply", "data": {"message_seq": message_seq}}]

        try:
            message_seq = int(target_message_id)
        except ValueError:
            return []
        return [{"type": "reply", "data": {"message_seq": message_seq}}]

    def _build_face_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """构造 QQ 原生表情消息段。"""
        item_data = item.get("data")
        face_id = ""
        if isinstance(item_data, Mapping):
            face_id = str(item_data.get("id") or "").strip()
        else:
            face_id = str(item_data or "").strip()
        if not face_id:
            return []
        return [{"type": "face", "data": {"face_id": face_id, "is_large": False}}]

    def _build_image_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        binary_base64 = str(item.get("binary_data_base64") or "").strip()
        if binary_base64:
            return [{"type": "image", "data": {"uri": f"base64://{binary_base64}", "sub_type": "normal"}}]

        item_data = item.get("data")
        url = ""
        if isinstance(item_data, Mapping):
            url = str(item_data.get("url") or item_data.get("file") or "").strip()
        else:
            url = str(item_data or "").strip()

        if not url:
            return []
        if not url.startswith(("http://", "https://", "file://", "base64://")):
            url = f"file://{url}"
        return [{"type": "image", "data": {"uri": url, "sub_type": "normal"}}]

    def _build_emoji_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        binary_base64 = str(item.get("binary_data_base64") or "").strip()
        if binary_base64:
            return [{"type": "image", "data": {"uri": f"base64://{binary_base64}", "sub_type": "sticker"}}]

        item_data = item.get("data")
        url = ""
        if isinstance(item_data, Mapping):
            url = str(item_data.get("url") or item_data.get("file") or "").strip()
        else:
            url = str(item_data or "").strip()

        if not url:
            return []
        if not url.startswith(("http://", "https://", "file://", "base64://")):
            url = f"file://{url}"
        return [{"type": "image", "data": {"uri": url, "sub_type": "sticker"}}]

    def _build_voice_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        binary_base64 = str(item.get("binary_data_base64") or "").strip()
        if binary_base64:
            return [{"type": "record", "data": {"uri": f"base64://{binary_base64}"}}]

        item_data = item.get("data")
        url = ""
        if isinstance(item_data, Mapping):
            url = str(item_data.get("url") or item_data.get("file") or "").strip()
        else:
            url = str(item_data or "").strip()

        if not url:
            return []
        if not url.startswith(("http://", "https://", "file://", "base64://")):
            url = f"file://{url}"
        return [{"type": "record", "data": {"uri": url}}]

    def _build_video_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        binary_base64 = str(item.get("binary_data_base64") or "").strip()
        if binary_base64:
            return [{"type": "video", "data": {"uri": f"base64://{binary_base64}"}}]

        item_data = item.get("data")
        url = ""
        if isinstance(item_data, Mapping):
            url = str(item_data.get("url") or item_data.get("file") or "").strip()
        else:
            url = str(item_data or "").strip()

        if not url:
            return []
        if not url.startswith(("http://", "https://", "file://", "base64://")):
            url = f"file://{url}"
        return [{"type": "video", "data": {"uri": url}}]

    def _build_file_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        item_data = item.get("data")
        if isinstance(item_data, str):
            normalized_file = item_data.strip()
            if not normalized_file:
                return []
            if not normalized_file.startswith(("http://", "https://", "file://", "base64://")):
                normalized_file = f"file://{normalized_file}"
            return [{"type": "file", "data": {"file_uri": normalized_file, "file_name": "file"}}]

        if not isinstance(item_data, Mapping):
            return []

        raw_file = str(item_data.get("file") or item_data.get("path") or item_data.get("url") or "").strip()
        file_name = str(item_data.get("name") or "file").strip()
        if not raw_file:
            return []
        if not raw_file.startswith(("http://", "https://", "file://", "base64://")):
            raw_file = f"file://{raw_file}"
        return [{"type": "file", "data": {"file_uri": raw_file, "file_name": file_name}}]

    def _build_forward_segments(self, item: Mapping[str, Any]) -> List[Dict[str, Any]]:
        item_data = item.get("data")
        if not isinstance(item_data, list):
            return []

        messages = []
        for node in item_data:
            if not isinstance(node, Mapping):
                continue
            content = node.get("content", [])
            node_segments = self.convert_segments(content)
            user_id = 0
            try:
                user_id = int(str(node.get("user_id") or "0").strip())
            except ValueError:
                pass
            sender_name = str(node.get("user_nickname") or node.get("user_cardname") or "QQ用户")
            messages.append({
                "user_id": user_id,
                "sender_name": sender_name,
                "segments": node_segments,
            })

        if not messages:
            return []
        return [{"type": "forward", "data": {"messages": messages}}]
