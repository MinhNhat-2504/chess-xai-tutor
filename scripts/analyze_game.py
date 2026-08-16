"""Phân tích PGN thành báo cáo XAI cho người học cờ.

Mặc định dùng Stockfish làm nguồn điểm số nếu tìm thấy (STOCKFISH_PATH, PATH,
hoặc engines/stockfish/); không có thì rơi về Alpha-Beta nội bộ.

Ví dụ:
    python scripts/analyze_game.py data/game.pgn --output experiments/results/xai_report.json
    python scripts/analyze_game.py data/game.pgn --no-stockfish --depth 2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import chess.pgn
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.xai import MoveExplainer

# PowerShell cũ trên Windows có thể dùng cp1252; báo cáo/CLI này cần in tiếng Việt.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def load_xai_config(config_path: Path) -> dict:
    """Đọc mục ``xai`` trong config.yaml; thiếu file hay thiếu mục đều trả {}."""
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return cfg.get("xai", {}) or {}
    except Exception:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Giải thích từng nước đi trong một file PGN.")
    parser.add_argument("pgn", type=Path, help="File PGN đầu vào")
    parser.add_argument("--depth", type=int, default=2, help="Độ sâu Alpha-Beta khi fallback (mặc định: 2)")
    parser.add_argument("--engine-path", type=Path, default=None, help="Đường dẫn Stockfish (mặc định: tự dò)")
    parser.add_argument("--engine-depth", type=int, default=None, help="Độ sâu Stockfish (mặc định: 12; 16 = phân tích kỹ)")
    parser.add_argument("--no-stockfish", action="store_true", help="Chỉ dùng engine nội bộ")
    parser.add_argument("--max-plies", type=int, default=None, help="Chỉ phân tích N nửa-nước đầu")
    parser.add_argument("--output", type=Path, help="File JSON; mặc định in ra stdout")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config" / "config.yaml")
    args = parser.parse_args()

    with args.pgn.open(encoding="utf-8") as handle:
        game = chess.pgn.read_game(handle)
    if game is None:
        raise SystemExit("Không đọc được ván cờ nào từ PGN.")

    moves = list(game.mainline_moves())
    if args.max_plies is not None:
        moves = moves[:max(0, args.max_plies)]
    starting_fen = game.headers.get("FEN")

    xai_cfg = load_xai_config(args.config)
    use_stockfish = (not args.no_stockfish) and xai_cfg.get("use_stockfish", True)
    engine_path = args.engine_path or xai_cfg.get("engine_path")
    engine_depth = args.engine_depth or int(xai_cfg.get("engine_depth", 12))

    explainer = MoveExplainer(
        depth=args.depth,
        use_stockfish=use_stockfish,
        engine_path=engine_path,
        engine_depth=engine_depth,
        multipv=int(xai_cfg.get("multipv", 3)),
        engine_time_s=xai_cfg.get("engine_time_s", 1.0),
    )
    print(f"Engine phân tích: {explainer.engine_label}", file=sys.stderr)
    try:
        analysis = explainer.analyze_game(moves, starting_fen=starting_fen)
    finally:
        explainer.close()

    payload = {
        "headers": dict(game.headers),
        "engine": explainer.engine_label,
        "analysis": analysis,
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"Đã lưu báo cáo XAI: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
