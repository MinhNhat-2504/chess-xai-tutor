"""Xuất ván cờ ra PGN chuẩn — Báo cáo mục 4.5.

PGN mở được trong lichess/chess.com analysis để kiểm tra chất lượng nước đi
hoặc đính kèm minh chứng vào báo cáo. Dùng `chess.pgn` của python-chess.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import chess
import chess.pgn


def game_to_pgn(
    moves: Iterable[chess.Move],
    white_name: str,
    black_name: str,
    result: str,
    headers_extra: dict | None = None,
    starting_fen: str | None = None,
) -> str:
    """Dựng PGN từ chuỗi nước đi đã chơi. `moves` đi theo thứ tự thời gian."""
    game = chess.pgn.Game()
    game.headers["Event"] = "Chess-AI Self-play Tournament"
    game.headers["Site"] = "VLU - DACN"
    game.headers["White"] = white_name
    game.headers["Black"] = black_name
    game.headers["Result"] = result
    if starting_fen and starting_fen != chess.STARTING_FEN:
        game.headers["FEN"] = starting_fen
        game.headers["SetUp"] = "1"
    if headers_extra:
        for k, v in headers_extra.items():
            game.headers[k] = str(v)

    board = chess.Board(starting_fen) if starting_fen else chess.Board()
    node = game
    for move in moves:
        node = node.add_variation(move)
        board.push(move)

    return str(game)


def append_pgn_file(path, pgn_text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(pgn_text)
        f.write("\n\n")
