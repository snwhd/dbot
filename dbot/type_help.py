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


def try_type(
    o: Any,
    t: Type[T],
    d: Optional[T] = None,
) -> Optional[T]:
    if isinstance(o, t):
        return o
    return d


def expect_type_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
    t: Type[T],
) -> T:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return assert_type(d.get(k), t)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return assert_type(d[k], t)
    raise ValueError(f'unsupported data type: {type(d)}')


def try_type_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
    t: Type[T],
    e: Optional[T],
) -> Optional[T]:
    if isinstance(d, dict):
        assert isinstance(k, str)
        return try_type(d.get(k, e), t, e)
    elif isinstance(d, list) or isinstance(d, tuple):
        assert isinstance(k, int)
        return try_type(d[k], t, e)
    raise ValueError(f'unsupported data type: {type(d)}')


def expect_int_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> int:
    return expect_type_in(d, k, int)


def expect_float_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> float:
    return expect_type_in(d, k, float)


def expect_str_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> str:
    return expect_type_in(d, k, str)


def expect_list_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> list:
    return expect_type_in(d, k, list)


def expect_dict_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> dict:
    return expect_type_in(d, k, dict)


def expect_bool_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
) -> bool:
    return expect_type_in(d, k, bool)


def try_int_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
    e: Optional[int] = None
) -> Optional[int]:
    return try_type_in(d, k, int, e)


def try_float_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
    e: Optional[float] = None,
) -> Optional[float]:
    return try_type_in(d, k, float, e)


def try_str_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
    e: Optional[str] = None,
) -> Optional[str]:
    return try_type_in(d, k, str, e)


def try_list_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
    e: Optional[list] = None,
) -> Optional[list]:
    return try_type_in(d, k, list, e)


def try_dict_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
    e: Optional[dict] = None,
) -> Optional[dict]:
    return try_type_in(d, k, dict, e)


def try_bool_in(
    d: Union[Collection[Any], Dict[str, Any]],
    k: Union[int, str],
    e: Optional[bool] = None,
) -> Optional[bool]:
    return try_type_in(d, k, bool, e)
