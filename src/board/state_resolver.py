"""Chọn hàm mã hoá state cho Q-learning experiments."""
from .state import state_key as default_state_key


def resolve_state_key_fn(name: str):
    if name == "compact":
        from .compact_state import compact_state_key
        return compact_state_key
    if name == "full":
        return default_state_key
    raise ValueError(f"Unsupported state representation: {name}")
