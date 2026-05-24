"""Milky 内置适配器配置模型。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar, Dict, List, Literal, Optional, Tuple

import logging

from maibot_sdk import Field, PluginConfigBase
from pydantic import ValidationInfo, field_validator, model_validator

from .constants import (
    DEFAULT_ACTION_TIMEOUT_SEC,
    DEFAULT_CHAT_LIST_TYPE,
    DEFAULT_HEARTBEAT_INTERVAL_SEC,
    DEFAULT_MILKY_HOST,
    DEFAULT_MILKY_PORT,
    DEFAULT_RECONNECT_DELAY_SEC,
    SUPPORTED_CONFIG_VERSION,
)

LOGGER = logging.getLogger("milky_adapter.config")


class MilkyPluginOptions(PluginConfigBase):
    """插件级配置。"""

    __ui_label__: ClassVar[str] = "插件设置"
    __ui_order__: ClassVar[int] = 0

    enabled: bool = Field(
        default=False,
        description="是否启用 Milky 适配器。",
        json_schema_extra={
            "hint": "关闭后插件会保持空闲，不会主动建立 Milky 连接。",
            "label": "启用适配器",
            "order": 0,
        },
    )
    config_version: str = Field(
        default=SUPPORTED_CONFIG_VERSION,
        description="当前配置结构版本。",
        json_schema_extra={
            "disabled": True,
            "hidden": True,
            "label": "配置版本",
            "order": 99,
        },
    )

    def should_connect(self) -> bool:
        return self.enabled

    @field_validator("config_version", mode="before")
    @classmethod
    def _normalize_config_version(cls, value: Any) -> str:
        normalized_value = _normalize_string(value)
        return normalized_value or SUPPORTED_CONFIG_VERSION


class MilkyServerConfig(PluginConfigBase):
    """Milky 协议端连接配置。"""

    __ui_label__: ClassVar[str] = "Milky 连接"
    __ui_order__: ClassVar[int] = 1

    host: str = Field(
        default=DEFAULT_MILKY_HOST,
        description="Milky 协议端主机地址。",
        json_schema_extra={
            "hint": "通常为运行 Milky 协议端的宿主机地址，默认使用本机回环地址。",
            "label": "主机地址",
            "order": 0,
            "placeholder": "127.0.0.1",
        },
    )
    port: int = Field(
        default=DEFAULT_MILKY_PORT,
        description="Milky 协议端 HTTP 服务端口。",
        json_schema_extra={
            "hint": "与 Milky 协议端 HTTP 服务监听端口保持一致。",
            "label": "端口",
            "order": 1,
        },
    )
    token: str = Field(
        default="",
        description="Milky 访问令牌，未启用鉴权时可留空。",
        json_schema_extra={
            "hint": "若 Milky 协议端开启了访问令牌校验，请在这里填写相同的 token。",
            "input_type": "password",
            "label": "访问令牌",
            "order": 2,
            "placeholder": "可留空",
        },
    )
    event_mode: Literal["websocket", "sse"] = Field(
        default="websocket",
        description="事件接收模式。",
        json_schema_extra={
            "hint": "WebSocket 模式使用双向通信，SSE 模式使用服务器推送。",
            "label": "事件模式",
            "order": 3,
        },
    )
    reconnect_delay_sec: float = Field(
        default=DEFAULT_RECONNECT_DELAY_SEC,
        description="连接断开后的重连等待时间，单位为秒。",
        json_schema_extra={
            "hint": "连接断开后会等待该时长再尝试重新连接。",
            "label": "重连等待（秒）",
            "order": 4,
            "step": 1,
        },
    )
    action_timeout_sec: float = Field(
        default=DEFAULT_ACTION_TIMEOUT_SEC,
        description="调用 Milky API 的超时时间，单位为秒。",
        json_schema_extra={
            "hint": "发送消息、查询信息等动作会在超时后报错。",
            "label": "动作超时（秒）",
            "order": 5,
            "step": 1,
        },
    )
    connection_id: str = Field(
        default="",
        description="可选连接标识，用于区分多条 Milky 链路。",
        json_schema_extra={
            "hint": "当存在多条 Milky 连接时，可用它作为路由作用域标识。",
            "label": "连接标识",
            "order": 6,
            "placeholder": "例如：primary",
        },
    )

    def build_api_url(self, api_name: str) -> str:
        return f"http://{self.host}:{self.port}/api/{api_name}"

    def build_event_url(self) -> str:
        return f"http://{self.host}:{self.port}/event"

    def build_event_ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/event"

    @field_validator("host", mode="before")
    @classmethod
    def _normalize_host(cls, value: Any) -> str:
        normalized_value = _normalize_string(value)
        return normalized_value or DEFAULT_MILKY_HOST

    @field_validator("port", mode="before")
    @classmethod
    def _normalize_port(cls, value: Any) -> int:
        return _normalize_positive_int(value, DEFAULT_MILKY_PORT)

    @field_validator("token", "connection_id", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str:
        return _normalize_string(value)

    @field_validator("event_mode", mode="before")
    @classmethod
    def _normalize_event_mode(cls, value: Any) -> Literal["websocket", "sse"]:
        normalized = _normalize_string(value).lower()
        if normalized in ("websocket", "ws"):
            return "websocket"
        if normalized == "sse":
            return "sse"
        return "websocket"

    @field_validator("reconnect_delay_sec", "action_timeout_sec", mode="before")
    @classmethod
    def _normalize_positive_float_fields(cls, value: Any, info: ValidationInfo) -> float:
        default_values: Dict[str, float] = {
            "action_timeout_sec": DEFAULT_ACTION_TIMEOUT_SEC,
            "reconnect_delay_sec": DEFAULT_RECONNECT_DELAY_SEC,
        }
        return _normalize_positive_float(value, default_values[str(info.field_name)])


class MilkyChatConfig(PluginConfigBase):
    """聊天名单配置。"""

    __ui_label__: ClassVar[str] = "聊天过滤"
    __ui_order__: ClassVar[int] = 2

    enable_chat_list_filter: bool = Field(
        default=True,
        description="是否启用群聊与私聊名单过滤。",
        json_schema_extra={
            "hint": "关闭后将忽略群聊名单和私聊名单，仅保留全局屏蔽用户。",
            "label": "启用聊天名单过滤",
            "order": 0,
        },
    )
    show_dropped_chat_list_messages: bool = Field(
        default=False,
        description="是否显示未通过聊天名单过滤而被丢弃的消息日志。",
        json_schema_extra={
            "hint": "关闭后不会记录群聊/私聊因未通过聊天名单过滤而被丢弃的日志。",
            "label": "显示聊天名单丢弃日志",
            "order": 1,
        },
    )
    group_list_type: Literal["whitelist", "blacklist"] = Field(
        default=DEFAULT_CHAT_LIST_TYPE,
        description="群聊名单模式。",
        json_schema_extra={
            "hint": "白名单模式只接收列表内群聊，黑名单模式则忽略列表内群聊。",
            "label": "群聊名单模式",
            "order": 2,
        },
    )
    group_list: List[str] = Field(
        default_factory=list,
        description="群聊名单中的群号列表。",
        json_schema_extra={
            "hint": "群号会被统一转换为字符串并自动去重。",
            "label": "群聊名单",
            "order": 3,
            "placeholder": "请输入群号",
        },
    )
    private_list_type: Literal["whitelist", "blacklist"] = Field(
        default=DEFAULT_CHAT_LIST_TYPE,
        description="私聊名单模式。",
        json_schema_extra={
            "hint": "白名单模式只接收列表内私聊，黑名单模式则忽略列表内私聊。",
            "label": "私聊名单模式",
            "order": 4,
        },
    )
    private_list: List[str] = Field(
        default_factory=list,
        description="私聊名单中的用户 ID 列表。",
        json_schema_extra={
            "hint": "用户 ID 会被统一转换为字符串并自动去重。",
            "label": "私聊名单",
            "order": 5,
            "placeholder": "请输入用户 ID",
        },
    )
    ban_user_id: List[str] = Field(
        default_factory=list,
        description="全局屏蔽的用户 ID 列表。",
        json_schema_extra={
            "hint": "这些用户的消息会在进入 Host 之前被直接丢弃。",
            "label": "全局屏蔽用户",
            "order": 6,
            "placeholder": "请输入用户 ID",
        },
    )

    @field_validator("group_list_type", "private_list_type", mode="before")
    @classmethod
    def _normalize_list_types(cls, value: Any) -> Literal["whitelist", "blacklist"]:
        return _normalize_list_mode(value)

    @field_validator("group_list", "private_list", "ban_user_id", mode="before")
    @classmethod
    def _normalize_id_lists(cls, value: Any) -> List[str]:
        return _normalize_string_list(value)


class MilkyFilterConfig(PluginConfigBase):
    """消息过滤配置。"""

    __ui_label__: ClassVar[str] = "消息过滤"
    __ui_order__: ClassVar[int] = 3

    ignore_self_message: bool = Field(
        default=True,
        description="是否忽略机器人自身发送的消息。",
        json_schema_extra={
            "hint": "建议保持开启，避免机器人处理自己刚刚发出的消息。",
            "label": "忽略自身消息",
            "order": 0,
        },
    )
    regex_filter_enabled: bool = Field(
        default=False,
        description="是否启用正则表达式消息过滤。",
        json_schema_extra={
            "hint": "开启后将根据正则表达式规则过滤入站消息。",
            "label": "启用正则过滤",
            "order": 1,
        },
    )
    regex_filter_mode: Literal["blacklist", "whitelist"] = Field(
        default="blacklist",
        description="正则过滤模式。blacklist 匹配则丢弃，whitelist 仅放行匹配的消息。",
        json_schema_extra={
            "hint": "黑名单模式下匹配正则的消息会被丢弃；白名单模式下仅匹配正则的消息会被放行。",
            "label": "正则过滤模式",
            "order": 2,
        },
    )
    regex_filter_patterns: List[str] = Field(
        default_factory=list,
        description="正则表达式列表，支持 Python re 模块语法。",
        json_schema_extra={
            "hint": "每条规则为一个 Python 正则表达式，消息文本将逐条匹配。",
            "label": "正则表达式列表",
            "order": 3,
            "placeholder": r"例如：^广告.*|spam",
        },
    )
    regex_filter_show_dropped: bool = Field(
        default=False,
        description="是否显示未通过正则过滤而被丢弃的消息日志。",
        json_schema_extra={
            "hint": "关闭后不会记录因正则过滤而被丢弃的日志。",
            "label": "显示正则过滤丢弃日志",
            "order": 4,
        },
    )

    @field_validator("regex_filter_mode", mode="before")
    @classmethod
    def _normalize_regex_filter_mode(cls, value: Any) -> Literal["whitelist", "blacklist"]:
        normalized_value = _normalize_string(value)
        if normalized_value == "whitelist":
            return "whitelist"
        if normalized_value not in ("whitelist", "blacklist"):
            LOGGER.warning(f"无效的 regex_filter_mode 值 '{value}'，已回退到 'blacklist'")
        return "blacklist"

    @field_validator("regex_filter_patterns", mode="before")
    @classmethod
    def _normalize_regex_filter_patterns(cls, value: Any) -> List[str]:
        return _normalize_string_list(value)


class MilkyPluginSettings(PluginConfigBase):
    """Milky 插件完整配置。"""

    plugin: MilkyPluginOptions = Field(default_factory=MilkyPluginOptions)
    milky_server: MilkyServerConfig = Field(default_factory=MilkyServerConfig)
    chat: MilkyChatConfig = Field(default_factory=MilkyChatConfig)
    filters: MilkyFilterConfig = Field(default_factory=MilkyFilterConfig)

    @classmethod
    def from_mapping(cls, raw_config: Mapping[str, Any], logger: Any) -> "MilkyPluginSettings":
        del logger
        return cls.model_validate(dict(raw_config))

    def should_connect(self) -> bool:
        return self.plugin.should_connect()

    def validate_runtime_config(self, logger: Any) -> bool:
        config_version = self.plugin.config_version
        if not config_version:
            logger.error(f"Milky 适配器配置缺少 plugin.config_version，当前插件要求版本 {SUPPORTED_CONFIG_VERSION}")
            return False

        if config_version != SUPPORTED_CONFIG_VERSION:
            logger.error(
                f"Milky 适配器配置版本不兼容: 当前为 {config_version}，当前插件要求 {SUPPORTED_CONFIG_VERSION}"
            )
            return False

        if not self.milky_server.host:
            logger.warning("Milky 适配器已启用，但 milky_server.host 为空")
            return False

        if self.milky_server.port <= 0:
            logger.warning("Milky 适配器已启用，但 milky_server.port 不是正整数")
            return False

        return True


def _normalize_list_mode(value: Any) -> Literal["whitelist", "blacklist"]:
    normalized_value = _normalize_string(value)
    if normalized_value == "whitelist":
        return "whitelist"
    if normalized_value == "blacklist":
        return "blacklist"
    return DEFAULT_CHAT_LIST_TYPE


def _normalize_positive_float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)) and float(value) > 0:
        return float(value)
    if isinstance(value, str):
        try:
            parsed_value = float(value.strip())
        except ValueError:
            return default
        if parsed_value > 0:
            return parsed_value
    return default


def _normalize_positive_int(value: Any, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        normalized_value = value.strip()
        if normalized_value.isdigit():
            parsed_value = int(normalized_value)
            if parsed_value > 0:
                return parsed_value
    return default


def _normalize_string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalize_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    normalized_values: List[str] = []
    seen_values = set()
    for item in value:
        item_text = _normalize_string(item)
        if not item_text or item_text in seen_values:
            continue
        seen_values.add(item_text)
        normalized_values.append(item_text)
    return normalized_values
