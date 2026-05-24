"""Milky 入站消息过滤。"""

from __future__ import annotations

import re
from typing import Any, Collection, List, Pattern

from .config import MilkyChatConfig, MilkyFilterConfig


class MilkyRegexFilter:
    """Milky 正则表达式消息内容过滤器。"""

    def __init__(self, logger: Any) -> None:
        self._logger = logger
        self._compiled_patterns: List[Pattern[str]] = []
        self._source_patterns: List[str] = []

    def reload_patterns(self, patterns: List[str]) -> None:
        compiled: List[Pattern[str]] = []
        source: List[str] = []
        for pattern_text in patterns:
            try:
                compiled.append(re.compile(pattern_text))
                source.append(pattern_text)
            except re.error as exc:
                self._logger.warning(f"Milky 正则过滤器忽略无效正则表达式 '{pattern_text}': {exc}")
        self._compiled_patterns = compiled
        self._source_patterns = source
        self._logger.debug(f"Milky 正则过滤器已加载 {len(compiled)} 条规则: {source}")

    def is_message_allowed(self, plain_text: str, filter_config: MilkyFilterConfig) -> bool:
        if not filter_config.regex_filter_enabled:
            return True

        if not self._compiled_patterns:
            if filter_config.regex_filter_mode == "whitelist":
                if filter_config.regex_filter_show_dropped:
                    self._logger.warning("Milky 白名单正则过滤器无有效规则，消息被丢弃")
                return False
            return True

        matched = self._matches_any_pattern(plain_text)

        if filter_config.regex_filter_mode == "blacklist":
            if matched:
                if filter_config.regex_filter_show_dropped:
                    self._logger.warning(f"Milky 消息匹配黑名单正则，消息被丢弃: {plain_text!r}")
                return False
            return True

        if not matched:
            if filter_config.regex_filter_show_dropped:
                self._logger.warning(f"Milky 消息未匹配白名单正则，消息被丢弃: {plain_text!r}")
            return False
        return True

    def _matches_any_pattern(self, text: str) -> bool:
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return True
        return False


class MilkyChatFilter:
    """Milky 聊天名单过滤器。"""

    def __init__(self, logger: Any) -> None:
        self._logger = logger

    def is_inbound_chat_allowed(
        self,
        sender_user_id: str,
        group_id: str,
        chat_config: MilkyChatConfig,
    ) -> bool:
        if sender_user_id in chat_config.ban_user_id:
            self._logger.warning(f"Milky 用户 {sender_user_id} 在全局禁止名单中，消息被丢弃")
            return False

        if not chat_config.enable_chat_list_filter:
            return True

        if group_id:
            if not self._is_id_allowed_by_list_policy(group_id, chat_config.group_list_type, chat_config.group_list):
                if chat_config.show_dropped_chat_list_messages:
                    self._logger.warning(f"Milky 群聊 {group_id} 未通过聊天名单过滤，消息被丢弃")
                return False
            return True

        if not self._is_id_allowed_by_list_policy(
            sender_user_id,
            chat_config.private_list_type,
            chat_config.private_list,
        ):
            if chat_config.show_dropped_chat_list_messages:
                self._logger.warning(f"Milky 私聊用户 {sender_user_id} 未通过聊天名单过滤，消息被丢弃")
            return False
        return True

    @staticmethod
    def _is_id_allowed_by_list_policy(target_id: str, list_type: str, configured_ids: Collection[str]) -> bool:
        if list_type == "whitelist":
            return target_id in configured_ids
        return target_id not in configured_ids
