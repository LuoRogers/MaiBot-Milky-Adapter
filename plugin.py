"""内置 Milky 适配器插件。

当前实现承担完整的 QQ / Milky 消息网关职责：
1. 作为客户端连接 Milky 协议端的事件流（SSE/WebSocket）。
2. 通过 HTTP POST 调用 Milky API。
3. 将入站消息与通知事件转换为 Host 侧结构。
4. 将 Host 出站消息转换为 Milky API 调用并发送。
5. 通过公开 API 暴露 QQ 平台专属查询与管理动作。
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Mapping, Optional, cast

from maibot_sdk import MaiBotPlugin, MessageGateway, PluginConfigBase

from .apis import (
    MilkyAccountApiMixin,
    MilkyFileApiMixin,
    MilkyGroupApiMixin,
    MilkyMessageApiMixin,
    MilkySystemApiMixin,
)
from .config import MilkyPluginSettings
from .constants import MILKY_GATEWAY_NAME
from .runtime import MilkyEventRouter, MilkyRuntimeBuilder, MilkyRuntimeBundle
from .services import MilkyActionService, MilkyQueryService


class MilkyAdapterPlugin(
    MilkyAccountApiMixin,
    MilkyFileApiMixin,
    MilkyGroupApiMixin,
    MilkyMessageApiMixin,
    MilkySystemApiMixin,
    MaiBotPlugin,
):
    """Milky 消息网关与 QQ 能力插件。"""

    config_model: ClassVar[type[PluginConfigBase] | None] = MilkyPluginSettings

    def __init__(self) -> None:
        super().__init__()
        self._action_service: Optional[MilkyActionService] = None
        self._query_service: Optional[MilkyQueryService] = None
        self._event_router: Optional[MilkyEventRouter] = None
        self._runtime_bundle: Optional[MilkyRuntimeBundle] = None

    async def on_load(self) -> None:
        await self._restart_connection_if_needed()

    async def on_unload(self) -> None:
        await self._stop_connection()

    async def on_config_update(self, scope: str, config_data: Dict[str, Any], version: str) -> None:
        if scope != "self":
            return

        self.set_plugin_config(config_data)
        if version:
            self.ctx.logger.debug(f"Milky 适配器收到配置更新通知: {version}")
        await self._restart_connection_if_needed()

    @MessageGateway(
        name=MILKY_GATEWAY_NAME,
        route_type="duplex",
        platform="qq",
        protocol="milky",
        description="Milky HTTP/SSE 双工消息网关",
    )
    async def handle_milky_gateway(
        self,
        message: Dict[str, Any],
        route: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        del metadata
        del kwargs

        runtime_bundle = self._require_runtime_bundle()
        try:
            action_name, params = runtime_bundle.outbound_codec.build_outbound_action(message, route or {})
            response = await runtime_bundle.action_service.call_action(action_name, params)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        if str(response.get("status", "")).lower() != "ok":
            return {
                "success": False,
                "error": str(response.get("message") or "Milky send failed"),
                "metadata": {"retcode": response.get("retcode")},
            }

        response_data = response.get("data", {})
        external_message_id = ""
        if isinstance(response_data, Mapping):
            message_seq = response_data.get("message_seq")
            if message_seq is not None:
                external_message_id = str(message_seq)

        return {
            "success": True,
            "external_message_id": external_message_id or None,
            "metadata": {
                "action": action_name,
                "data": response_data if isinstance(response_data, Mapping) else {},
            },
        }

    def _ensure_runtime_components(self) -> None:
        if self._event_router is None:
            self._event_router = MilkyEventRouter(
                gateway_capability=self.ctx.gateway,
                logger=self.ctx.logger,
                gateway_name=MILKY_GATEWAY_NAME,
                load_settings=self._load_settings,
            )

        if self._runtime_bundle is None:
            runtime_builder = MilkyRuntimeBuilder(
                gateway_capability=self.ctx.gateway,
                logger=self.ctx.logger,
                gateway_name=MILKY_GATEWAY_NAME,
            )
            self._runtime_bundle = runtime_builder.build(
                on_connection_opened=self._event_router.bootstrap_adapter_runtime_state,
                on_connection_closed=self._event_router.handle_transport_disconnected,
                on_payload=self._event_router.handle_transport_payload,
                on_heartbeat_timeout=self._event_router.handle_heartbeat_timeout,
            )
            self._event_router.bind_runtime(self._runtime_bundle)
            self._bind_runtime_aliases(self._runtime_bundle)

    def _bind_runtime_aliases(self, runtime_bundle: MilkyRuntimeBundle) -> None:
        self._action_service = runtime_bundle.action_service
        self._query_service = runtime_bundle.query_service

    def _load_settings(self) -> MilkyPluginSettings:
        return cast(MilkyPluginSettings, self.config)

    async def _restart_connection_if_needed(self) -> None:
        self._ensure_runtime_components()
        runtime_bundle = self._require_runtime_bundle()
        settings = self._load_settings()

        await self._stop_connection()
        if not settings.should_connect():
            self.ctx.logger.info("Milky 适配器保持空闲状态，因为插件或配置未启用")
            return
        if not settings.validate_runtime_config(self.ctx.logger):
            return
        if not runtime_bundle.transport.is_available():
            self.ctx.logger.error("Milky 适配器依赖 aiohttp，但当前环境未安装该依赖")
            return

        if not settings.chat.enable_chat_list_filter:
            self.ctx.logger.info(
                "Milky 聊天名单过滤已关闭：将忽略 group_list 与 private_list，仅保留 ban_user_id 规则"
            )

        runtime_bundle.regex_filter.reload_patterns(settings.filters.regex_filter_patterns)
        if settings.filters.regex_filter_enabled and settings.filters.regex_filter_patterns:
            self.ctx.logger.info(
                f"Milky 正则消息过滤已启用: 模式={settings.filters.regex_filter_mode}，"
                f"规则数={len(settings.filters.regex_filter_patterns)}"
            )

        runtime_bundle.transport.configure(settings.milky_server)
        await runtime_bundle.transport.start()

    async def _stop_connection(self) -> None:
        runtime_bundle = self._runtime_bundle
        if runtime_bundle is None:
            return

        await runtime_bundle.transport.stop()
        if self._event_router is not None:
            self._event_router.reset_caches()

    def _require_runtime_bundle(self) -> MilkyRuntimeBundle:
        self._ensure_runtime_components()
        runtime_bundle = self._runtime_bundle
        if runtime_bundle is None:
            raise RuntimeError("Milky 运行时尚未初始化")
        return runtime_bundle


def create_plugin() -> MilkyAdapterPlugin:
    """创建插件实例。"""
    return MilkyAdapterPlugin()
