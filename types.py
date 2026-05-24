"""Milky 适配器内部共享类型。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping, Optional, TypeAlias

from typing_extensions import NotRequired, TypedDict


class MilkyIncomingSegment(TypedDict):
    """Milky 入站消息段结构。"""

    type: str
    data: Mapping[str, Any]


class MilkyHostMessageSegment(TypedDict):
    """适配器转换后写入 Host 的消息段结构。"""

    type: str
    data: Any
    hash: NotRequired[str]
    binary_data_base64: NotRequired[str]


MilkyActionParams: TypeAlias = Mapping[str, Any]
MilkyActionParamsInput: TypeAlias = Optional[Mapping[str, Any]]
MilkyActionResponse: TypeAlias = Dict[str, Any]
MilkyIdInput: TypeAlias = int | str
MilkyMutablePayload: TypeAlias = MutableMapping[str, Any]
MilkyOptionalIdInput: TypeAlias = int | str | None
MilkyPayload: TypeAlias = Mapping[str, Any]
MilkyPayloadDict: TypeAlias = Dict[str, Any]
MilkyPayloadList: TypeAlias = List[Dict[str, Any]]
MilkyIncomingSegments: TypeAlias = List[MilkyIncomingSegment]
MilkySegment: TypeAlias = MilkyHostMessageSegment
MilkySegments: TypeAlias = List[MilkyHostMessageSegment]
