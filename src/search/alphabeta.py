"""Minimax + Alpha-Beta Pruning — Mô hình 2. Báo cáo mục 2.4, 3.8.2.

Đã nâng cấp (so với bản gốc đồ án):
- Transposition table có bound flag EXACT/LOWER/UPPER + best_move (mục 2.4.5),
  thay vì chỉ lưu raw value như bản cũ (an toàn cho mọi cửa sổ α-β).
- Sẵn móc nối cho quiescence search (mục 2.4.3) và killer/history heuristic
  (mục 2.4.2) ở các phase nâng cấp tiếp theo; bật/tắt qua tham số.

Đếm visited / pruned / cache_hits / q_visited / q_cutoffs phục vụ tiêu chí mục 4.4.3.
"""
import math
from dataclasses import dataclass
from typing import Optional

from ..board.state import state_key
from .move_ordering import order_moves
from .transposition import TranspositionTable, TTFlag


@dataclass
class SearchStats:
    visited: int = 0
    pruned: int = 0
    cache_hits: int = 0
    q_visited: int = 0       # node bên trong quiescence (phase 2)
    q_cutoffs: int = 0       # stand-pat cutoff trong quiescence (phase 2)


def _prepend_tt_move(moves, tt_move_uci: Optional[str]):
    """Đưa tt_move (nếu vẫn hợp lệ trong vị trí) lên đầu list moves."""
    if not tt_move_uci:
        return moves
    for i, m in enumerate(moves):
        if m.uci() == tt_move_uci:
            if i == 0:
                return moves
            return [m] + moves[:i] + moves[i + 1:]
    return moves  # tt_move không còn legal — bỏ qua


def alphabeta(
    env,
    depth: int,
    alpha: float,
    beta: float,
    maximizing: bool,
    evaluate,
    stats: SearchStats,
    perspective,
    transposition: Optional[TranspositionTable] = None,
    killer_tbl=None,
    history_tbl=None,
    use_quiescence: bool = False,
    q_max_depth: int = 6,
    ply: int = 0,
) -> float:
    stats.visited += 1

    # --- Probe TT (lưu alpha gốc để xác định flag sau search) ---
    alpha_orig = alpha
    key = None
    tt_best_move: Optional[str] = None
    if transposition is not None:
        key = (state_key(env.board), perspective)
        cached_value, tt_best_move = transposition.probe(key, depth, alpha, beta)
        if cached_value is not None:
            stats.cache_hits += 1
            return cached_value

    # --- Terminal: cache EXACT, trả ngay ---
    if env.is_terminal():
        value = evaluate(env.board, perspective)
        if transposition is not None and key is not None:
            transposition.store(key, depth, value, TTFlag.EXACT, None)
        return value

    # --- Leaf: gọi quiescence nếu bật, ngược lại trả evaluate trực tiếp ---
    if depth <= 0:
        if use_quiescence:
            from .quiescence import quiescence
            return quiescence(
                env, alpha, beta, evaluate, stats, perspective, 0, q_max_depth
            )
        return evaluate(env.board, perspective)

    # --- Move ordering: tt_best_move lên đầu, rồi MVV-LVA + killers + history ---
    killers = killer_tbl.get(ply) if killer_tbl is not None else ()
    moves = _prepend_tt_move(
        order_moves(env.board, env.legal_moves(), killers=killers, history=history_tbl),
        tt_best_move,
    )

    best_move_uci: Optional[str] = None

    if maximizing:
        value = -math.inf
        for move in moves:
            is_capture = env.board.is_capture(move)
            env.push(move)
            child = alphabeta(
                env, depth - 1, alpha, beta, False, evaluate, stats, perspective,
                transposition, killer_tbl, history_tbl, use_quiescence, q_max_depth, ply + 1,
            )
            env.pop()
            if child > value:
                value, best_move_uci = child, move.uci()
            alpha = max(alpha, value)
            if alpha >= beta:
                stats.pruned += 1
                # Quiet move gây β-cutoff → ghi nhận killer + history
                if not is_capture:
                    if killer_tbl is not None:
                        killer_tbl.add(ply, move.uci())
                    if history_tbl is not None:
                        history_tbl.add(env.board, move, depth)
                break
    else:
        value = math.inf
        for move in moves:
            is_capture = env.board.is_capture(move)
            env.push(move)
            child = alphabeta(
                env, depth - 1, alpha, beta, True, evaluate, stats, perspective,
                transposition, killer_tbl, history_tbl, use_quiescence, q_max_depth, ply + 1,
            )
            env.pop()
            if child < value:
                value, best_move_uci = child, move.uci()
            beta = min(beta, value)
            if beta <= alpha:
                stats.pruned += 1
                if not is_capture:
                    if killer_tbl is not None:
                        killer_tbl.add(ply, move.uci())
                    if history_tbl is not None:
                        history_tbl.add(env.board, move, depth)
                break

    # --- Store TT với bound flag đúng (kể cả khi bị prune) ---
    if transposition is not None and key is not None:
        if value <= alpha_orig:
            flag = TTFlag.UPPER          # giá trị thực ≤ value (không cải thiện alpha)
        elif value >= beta:
            flag = TTFlag.LOWER          # giá trị thực ≥ value (đã beta-cutoff)
        else:
            flag = TTFlag.EXACT
        transposition.store(key, depth, value, flag, best_move_uci)

    return value
