"""Killer-moves & History heuristic — Báo cáo mục 2.4.2 (mở rộng).

Cả hai đều giúp move ordering tốt hơn → α-β cắt sớm hơn ở các iteration sau.

- **KillerTable**: với mỗi ply, nhớ tối đa 2 nước "không-ăn-quân" gây β-cutoff.
  Khi ở chính ply đó (trong iteration sau hoặc nhánh khác cùng iteration),
  thử các killer này NGAY SAU captures/promotions → thường tạo cutoff lại.

- **HistoryTable**: cộng dồn `depth²` vào điểm `(piece_type, to_square)` mỗi
  lần nước đi quiet gây cutoff. Dùng như tiebreaker khi ordering các quiet moves.
"""
from __future__ import annotations

from collections import defaultdict


class KillerTable:
    """Hai killer move per ply (UCI strings)."""

    def __init__(self) -> None:
        self.table: dict[int, list[str]] = {}

    def get(self, ply: int) -> tuple[str, ...]:
        return tuple(self.table.get(ply, ()))

    def add(self, ply: int, move_uci: str) -> None:
        slot = self.table.setdefault(ply, [])
        if move_uci in slot:
            return  # đã có — không trùng lặp
        slot.insert(0, move_uci)
        if len(slot) > 2:
            slot.pop()  # giữ tối đa 2

    def clear(self) -> None:
        self.table.clear()


class HistoryTable:
    """Lịch sử cutoff theo `(piece_type, to_square)`."""

    def __init__(self) -> None:
        self.scores: dict[tuple[int, int], int] = defaultdict(int)

    def add(self, board, move, depth: int) -> None:
        piece = board.piece_at(move.from_square)
        if piece is None:
            return
        self.scores[(piece.piece_type, move.to_square)] += depth * depth

    def score(self, board, move) -> int:
        piece = board.piece_at(move.from_square)
        if piece is None:
            return 0
        return self.scores.get((piece.piece_type, move.to_square), 0)

    def clear(self) -> None:
        self.scores.clear()
