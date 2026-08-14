"""Mở giao diện web: dán/upload PGN và xem phân tích trên trình duyệt.

Ví dụ:
    python scripts/web_app.py                 # http://127.0.0.1:8000
    python scripts/web_app.py --port 5000 --engine-depth 18
    python scripts/web_app.py --no-stockfish  # chỉ dùng engine nội bộ
"""
from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui.web_app import create_app

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def ensure_port(host: str, port: int) -> int:
    """Trả về cổng dùng được.

    Windows đôi khi chặn sẵn cả dải cổng (Hyper-V/WSL giữ riêng — lỗi WinError
    10013 "forbidden by its access permissions"), nên nếu cổng mong muốn không
    bind được thì tự chọn một cổng trống khác thay vì chết với traceback.
    """
    try:
        with socket.socket() as probe:
            probe.bind((host, port))
        return port
    except OSError:
        with socket.socket() as probe:
            probe.bind((host, 0))
            free_port = probe.getsockname()[1]
        print(f"[web] Cổng {port} bị hệ thống chặn hoặc đang bận — chuyển sang cổng {free_port}.")
        return free_port


def load_xai_config(config_path: Path) -> dict:
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return cfg.get("xai", {}) or {}
    except Exception:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Chess XAI Tutor — giao diện web")
    parser.add_argument("--host", default="127.0.0.1", help="Địa chỉ lắng nghe (mặc định chỉ máy này)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--depth", type=int, default=2, help="Độ sâu Alpha-Beta khi fallback")
    parser.add_argument("--engine-path", type=Path, default=None, help="Đường dẫn Stockfish (mặc định: tự dò)")
    parser.add_argument("--engine-depth", type=int, default=None, help="Độ sâu Stockfish (mặc định: 14)")
    parser.add_argument("--no-stockfish", action="store_true", help="Chỉ dùng engine nội bộ")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config" / "config.yaml")
    args = parser.parse_args()

    xai_cfg = load_xai_config(args.config)
    app = create_app(
        use_stockfish=(not args.no_stockfish) and xai_cfg.get("use_stockfish", True),
        engine_path=args.engine_path or xai_cfg.get("engine_path"),
        engine_depth=args.engine_depth or int(xai_cfg.get("engine_depth", 14)),
        multipv=int(xai_cfg.get("multipv", 5)),
        fallback_depth=args.depth,
    )
    port = ensure_port(args.host, args.port)
    print(f"Chess XAI Tutor đang chạy tại: http://{args.host}:{port}  (Ctrl+C để dừng)")
    app.run(host=args.host, port=port, debug=False)


if __name__ == "__main__":
    main()
