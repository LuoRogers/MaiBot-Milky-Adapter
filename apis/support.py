"""Milky API 端点的公共辅助能力。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, TypeAlias

from maibot_sdk import API

from ..types import MilkyActionParamsInput, MilkyActionResponse, MilkyIdInput

if TYPE_CHECKING:
    from ..services import MilkyActionService, MilkyQueryService


MilkyApiIdInput: TypeAlias = MilkyIdInput
MilkyApiParamsInput: TypeAlias = MilkyActionParamsInput


class MilkyApiSupportMixin:
    """Milky API 端点共享辅助逻辑。"""

    _action_service: Optional["MilkyActionService"]
    _query_service: Optional["MilkyQueryService"]

    def _ensure_runtime_components(self) -> None:
        raise NotImplementedError

    @staticmethod
    def _coerce_int(value: object, field_name: str, expectation: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{field_name} 必须是{expectation}")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            try:
                return int(value)
            except (OverflowError, ValueError) as exc:
                raise ValueError(f"{field_name} 必须是{expectation}") from exc
        if isinstance(value, str):
            normalized_value = value.strip()
            if not normalized_value:
                raise ValueError(f"{field_name} 必须是{expectation}")
            try:
                return int(normalized_value)
            except ValueError as exc:
                raise ValueError(f"{field_name} 必须是{expectation}") from exc
        raise ValueError(f"{field_name} 必须是{expectation}")

    def _require_query_service(self) -> "MilkyQueryService":
        self._ensure_runtime_components()
        query_service = self._query_service
        if query_service is None:
            raise RuntimeError("Milky 查询服务尚未初始化")
        return query_service

    def _require_action_service(self) -> "MilkyActionService":
        self._ensure_runtime_components()
        action_service = self._action_service
        if action_service is None:
            raise RuntimeError("Milky 动作服务尚未初始化")
        return action_service

    @staticmethod
    def _normalize_positive_int(value: object, field_name: str) -> int:
        normalized_value = MilkyApiSupportMixin._coerce_int(value, field_name, "正整数")
        if normalized_value <= 0:
            raise ValueError(f"{field_name} 必须是正整数")
        return normalized_value

    @staticmethod
    def _normalize_non_negative_int(value: object, field_name: str) -> int:
        normalized_value = MilkyApiSupportMixin._coerce_int(value, field_name, "非负整数")
        if normalized_value < 0:
            raise ValueError(f"{field_name} 必须是非负整数")
        return normalized_value

    @staticmethod
    def _normalize_non_empty_string(value: object, field_name: str) -> str:
        normalized_value = str(value or "").strip()
        if not normalized_value:
            raise ValueError(f"{field_name} 不能为空")
        return normalized_value

    @classmethod
    def _normalize_user_id_list(cls, values: object, field_name: str) -> List[int]:
        if not isinstance(values, list) or not values:
            raise ValueError(f"{field_name} 必须是非空数组")
        return [cls._normalize_positive_int(value, field_name) for value in values]

    @staticmethod
    def _normalize_params(params: MilkyApiParamsInput) -> Dict[str, Any]:
        if params is None:
            return {}
        if not isinstance(params, Mapping):
            raise ValueError("params 必须是对象")
        return {str(key): value for key, value in params.items()}

    async def _call_milky_action(
        self,
        action_name: str,
        params: MilkyApiParamsInput = None,
    ) -> MilkyActionResponse:
        normalized_action_name = self._normalize_non_empty_string(action_name, "action_name")
        normalized_params = self._normalize_params(params)
        return await self._require_action_service().call_action(normalized_action_name, normalized_params)

    async def _call_milky_action_data(
        self,
        action_name: str,
        params: MilkyApiParamsInput = None,
    ) -> Any:
        normalized_action_name = self._normalize_non_empty_string(action_name, "action_name")
        normalized_params = self._normalize_params(params)
        return await self._require_action_service().call_action_data(normalized_action_name, normalized_params)

    @API("adapter.milky.action.call", description="调用任意 Milky API", version="1", public=True)
    async def api_call_action(
        self,
        action_name: str = "",
        params: MilkyApiParamsInput = None,
    ) -> MilkyActionResponse:
        return await self._call_milky_action(action_name, params)

    @API("adapter.milky.action.call_data", description="调用任意 Milky API 并返回 data 字段", version="1", public=True)
    async def api_call_action_data(
        self,
        action_name: str = "",
        params: MilkyApiParamsInput = None,
    ) -> Any:
        return await self._call_milky_action_data(action_name, params)
