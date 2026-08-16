"""Mở ứng dụng đồ hoạ để phân tích PGN Chess.com/Lichess.

Mặc định dùng Stockfish làm nguồn điểm số nếu tìm thấy; không có thì rơi về
Alpha-Beta nội bộ với ``--depth``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui.xai_viewer import run_xai_viewer

# Giúp trợ giúp CLI in tiếng Việt được trong PowerShell dùng code page cũ.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chess XAI PGN viewer")
    parser.add_argument("--depth", type=int, default=2, help="Độ sâu Alpha-Beta khi fallback")
    parser.add_argument("--engine-path", type=Path, default=None, help="Đường dẫn Stockfish (mặc định: tự dò)")
    parser.add_argument("--engine-depth", type=int, default=12, help="Độ sâu Stockfish (12 nhanh, 16 kỹ)")
    parser.add_argument("--no-stockfish", action="store_true", help="Chỉ dùng engine nội bộ")
    parser.add_argument("--square-size", type=int, default=64, help="Kích thước một ô bàn cờ")
    args = parser.parse_args()
    run_xai_viewer(
        depth=args.depth,
        square_size=args.square_size,
        use_stockfish=not args.no_stockfish,
        engine_path=args.engine_path,
        engine_depth=args.engine_depth,
    )


if __name__ == "__main__":
    main()
