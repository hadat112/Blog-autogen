from typing import Dict, Type

from .base import BaseStep


_STEP_REGISTRY: Dict[str, Type[BaseStep]] = {}


def register_step(step_id: str):
    def decorator(step_cls: Type[BaseStep]):
        _STEP_REGISTRY[step_id] = step_cls
        step_cls.step_id = step_id
        return step_cls

    return decorator


def get_step_class(step_id: str) -> Type[BaseStep]:
    try:
        return _STEP_REGISTRY[step_id]
    except KeyError as exc:
        raise KeyError(f"Unknown pipeline step: {step_id}") from exc


def create_step(step_id: str, **kwargs) -> BaseStep:
    return get_step_class(step_id)(**kwargs)
