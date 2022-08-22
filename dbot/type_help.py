#!/usr/bin/env python3
from __future__ import annotations
from typing import (
    Any,
    Collection,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)


T = TypeVar('T')


def assert_type(o: Any, t: Type[T]) -> T:
    assert isinstance(o, t)
    return o


def try_type(o: Any, t: Type[T]) -> Optional[T]:
    if isinstance(o, t):
        return o
    return None


def expect_int(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> int:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], int)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], int)
    raise ValueError(f'unsupported data type: {type(d)}')


def expect_float(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> float:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], float)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], float)
    raise ValueError(f'unsupported data type: {type(d)}')


def expect_str(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> str:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], str)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], str)
    raise ValueError(f'unsupported data type: {type(d)}')


def expect_list(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> list:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], list)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], list)
    raise ValueError(f'unsupported data type: {type(d)}')


def expect_bool(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> bool:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d[k], bool)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], bool)
    raise ValueError(f'unsupported data type: {type(d)}')


def require_args(d: Union[List, Dict], l: int) -> None:
    if len(d) < l:
        raise ValueError('not enough data')
