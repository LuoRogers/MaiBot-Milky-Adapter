"""Milky 消息网关运行时状态管理。"""

from typing import Any, Optional, Protocol


class _GatewayCapabilityProtocol(Protocol):
    """消息网关能力代理协议。"""

    async def update_state(
        self,
        gateway_name: str,
        *,
        ready: bool,
        platform: str = "",
        account_id: str = "",
        scope: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """向 Host 上报消息网关运行时状态。"""
        ...


class MilkyRuntimeStateManager:
    """Milky 消息网关路由状态上报器。"""

    def __init__(
        self,
        gateway_capability: _GatewayCapabilityProtocol,
        logger: Any,
        gateway_name: str,
    ) -> None:
        self._gateway_capability = gateway_capability
        self._gateway_name = gateway_name
        self._logger = logger
        self._runtime_state_connected: bool = False
        self._reported_account_id: Optional[str] = None
        self._reported_scope: Optional[str] = None

    async def report_connected(self, account_id: str, connection_id: str, base_url: str) -> bool:
        normalized_account_id = str(account_id).strip()
        if not normalized_account_id:
            return False

        scope = connection_id or None
        if (
            self._runtime_state_connected
            and self._reported_account_id == normalized_account_id
            and self._reported_scope == scope
        ):
            return True

        accepted = False
        try:
            accepted = await self._gateway_capability.update_state(
                gateway_name=self._gateway_name,
                ready=True,
                platform="qq",
                account_id=normalized_account_id,
                scope=connection_id,
                metadata={"milky_url": base_url},
            )
        except Exception as exc:
            self._logger.warning(f"Milky 消息网关上报连接就绪状态失败: {exc}")
            return False

        if not accepted:
            self._logger.warning("Milky 消息网关连接已建立，但 Host 未接受运行时状态更新")
            return False

        self._runtime_state_connected = True
        self._reported_account_id = normalized_account_id
        self._reported_scope = scope
        self._logger.info(
            f"Milky 消息网关已激活路由: platform=qq account_id={normalized_account_id} "
            f"scope={self._reported_scope or '*'}"
        )
        return True

    async def report_disconnected(self) -> None:
        if not self._runtime_state_connected:
            self._reported_account_id = None
            self._reported_scope = None
            return

        try:
            await self._gateway_capability.update_state(
                gateway_name=self._gateway_name,
                ready=False,
                platform="qq",
            )
        except Exception as exc:
            self._logger.warning(f"Milky 消息网关上报断开状态失败: {exc}")
        finally:
            self._runtime_state_connected = False
            self._reported_account_id = None
            self._reported_scope = None
