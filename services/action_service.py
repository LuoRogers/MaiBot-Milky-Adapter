"""Milky 底层动作调用服务。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional

import asyncio

if TYPE_CHECKING:
    from ..transport import MilkyTransportClient


class MilkyActionService:
    """Milky 底层动作与资源访问服务。"""

    def __init__(self, logger: Any, transport: "MilkyTransportClient") -> None:
        self._logger = logger
        self._transport = transport

    async def call_action(self, action_name: str, params: Mapping[str, Any]) -> Dict[str, Any]:
        normalized_params = {str(key): value for key, value in params.items()}
        try:
            response = await self._transport.call_action(action_name, normalized_params)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Milky 动作执行失败: action={action_name} error={exc}") from exc

        if str(response.get("status") or "").lower() != "ok":
            error_message = str(response.get("message") or "unknown")
            raise RuntimeError(f"Milky 动作返回失败: action={action_name} message={error_message}")
        return response

    async def call_action_data(self, action_name: str, params: Mapping[str, Any]) -> Any:
        response = await self.call_action(action_name, params)
        return response.get("data")

    async def safe_call_action_data(self, action_name: str, params: Mapping[str, Any]) -> Any:
        try:
            return await self.call_action_data(action_name, params)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._logger.warning(f"Milky 查询动作执行失败: action={action_name} error={exc}")
            return None

    async def download_binary(self, url: str) -> Optional[bytes]:
        if not url:
            return None

        try:
            from aiohttp import ClientSession, ClientTimeout
        except ImportError:
            self._logger.warning("Milky 查询层缺少 aiohttp，无法下载远程资源")
            return None

        try:
            timeout = ClientTimeout(total=15)
            async with ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self._logger.warning(f"Milky 远程资源下载失败: status={response.status} url={url}")
                        return None
                    return await response.read()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._logger.warning(f"Milky 远程资源下载失败: {exc}")
            return None
