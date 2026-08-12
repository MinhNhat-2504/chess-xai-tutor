"""Transposition Table với bound flags — Báo cáo mục 2.4.5.

So với bản đồ án gốc (chỉ lưu raw `value` trong dict), bản này:
- Lưu kèm `flag ∈ {EXACT, LOWER, UPPER}` để TÁI SỬ DỤNG cached value AN TOÀN
  giữa các cửa sổ alpha-beta khác nhau (bản cũ trả cache ngay cả khi giá trị
  đến từ cửa sổ pruned → có thể sai về mặt thuật toán).
- Lưu kèm `best_move` (UCI) — gọi là TT-move — dùng cho PV ordering ở các
  iteration sâu hơn (hữu ích cho iterative deepening, mục 2.4.4).

Quy ước flag:
- EXACT  : `score` là giá trị chính xác của subtree (alpha < score < beta khi search).
- LOWER  : `score` là CẬN DƯỚI (xảy ra beta-cutoff), giá trị thực ≥ `score`.
- UPPER  : `score` là CẬN TRÊN (không cải thiện alpha gốc), giá trị thực ≤ `score`.
"""
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class TTFlag(IntEnum):
    EXACT = 0
    LOWER = 1
    UPPER = 2


@dataclass
class TTEntry:
    depth: int
    score: float
    flag: TTFlag
    best_move: Optional[str]  # UCI string của nước đi PV; None nếu chưa biết


class TranspositionTable:
    """Bảng băm trạng thái với bound flags + best_move.

    Key do bên gọi (alphabeta) xây dựng — thường là `(state_key, perspective)`.
    """

    def __init__(self) -> None:
        self.table: dict[tuple, TTEntry] = {}

    def probe(self, key, depth: int, alpha: float, beta: float):
        """Trả `(cutoff_value | None, best_move | None)`.

        - `cutoff_value` khác None → có thể dùng giá trị này thay vì search.
        - `best_move` khác None → dùng cho move ordering (cho dù không cutoff).
        """
        entry = self.table.get(key)
        if entry is None:
            return None, None
        best_move = entry.best_move
        if entry.depth < depth:
            # Độ sâu lưu trữ chưa đủ — chỉ dùng best_move để ordering.
            return None, best_move
        if entry.flag == TTFlag.EXACT:
            return entry.score, best_move
        if entry.flag == TTFlag.LOWER and entry.score >= beta:
            return entry.score, best_move
        if entry.flag == TTFlag.UPPER and entry.score <= alpha:
            return entry.score, best_move
        return None, best_move

    def store(self, key, depth: int, score: float, flag: TTFlag, best_move: Optional[str] = None) -> None:
        """Lưu entry; nếu đã có entry sâu hơn thì giữ entry cũ (depth-preferred)."""
        existing = self.table.get(key)
        if existing is not None and existing.depth > depth:
            return
        self.table[key] = TTEntry(depth=depth, score=score, flag=flag, best_move=best_move)

    def __len__(self) -> int:
        return len(self.table)

    def clear(self) -> None:
        self.table.clear()
