"""Điểm vào WSGI cho server thật (Hugging Face Spaces, Render, Docker...).

Chạy bằng waitress (một tiến trình, nhiều thread) — phù hợp vì job phân tích
được giữ trong bộ nhớ của tiến trình. Cấu hình lấy từ config/config.yaml, có
thể ghi đè bằng biến môi trường để chỉnh theo sức máy chủ:

    XAI_ENGINE_DEPTH=12   # giảm độ sâu nếu CPU yếu
    XAI_MULTIPV=3
    XAI_USE_STOCKFISH=0   # tắt Stockfish (chỉ engine nội bộ)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.ui.web_app import create_app  # noqa: E402


def _xai_config() -> dict:
    try:
        cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text(encoding="utf-8")) or {}
        return cfg.get("xai", {}) or {}
    except Exception:
        return {}


_cfg = _xai_config()
_use_stockfish = os.environ.get("XAI_USE_STOCKFISH", "1") not in ("0", "false", "False")

app = create_app(
    use_stockfish=_use_stockfish and _cfg.get("use_stockfish", True),
    engine_path=os.environ.get("STOCKFISH_PATH") or _cfg.get("engine_path"),
    engine_depth=int(os.environ.get("XAI_ENGINE_DEPTH", _cfg.get("engine_depth", 14))),
    multipv=int(os.environ.get("XAI_MULTIPV", _cfg.get("multipv", 5))),
)
