from typing import List, Callable, Any, Optional


def first_or_none(
    lst: List, condition: Optional[Callable] = None, default: Any = None
) -> Any:
    """Get first element matching condition or default value"""
    if not lst:
        return default
    if condition is None:
        return lst[0]
    return next((item for item in lst if condition(item)), default)


def last_or_none(lst: List, condition=None, default=None):
    """Get last element matching condition or default value"""
    if not lst:
        return default
    if condition is None:
        return lst[-1]
    return next((item for item in reversed(lst) if condition(item)), default)


def single_or_none(lst: List, condition=None, default=None):
    """Get single element matching condition, throw if multiple"""
    if not lst:
        return default
    if condition is None:
        return lst[0] if len(lst) == 1 else None

    results = [item for item in lst if condition(item)]
    return results[0] if len(results) == 1 else default
