"""Iterative deepening root search with optional time control."""
from __future__ import annotations

import math
import time
from typing import Callable, Optional

from ..board.state import state_key
from .alphabeta import SearchStats, alphabeta
from .heuristics import HistoryTable, KillerTable
from .move_ordering import order_moves
from .transposition import TTFlag, TranspositionTable


def search_iterative_root(
    env,
    max_depth: int,
    evaluate,
    perspective,
    time_limit_s: Optional[float] = None,
    use_quiescence: bool = False,
    q_max_depth: int = 6,
    killer_tbl=None,
    history_tbl=None,
    use_killer_moves: bool = True,
    use_history_heuristic: bool = True,
    root_bonus_fn: Optional[Callable[[str], float]] = None,
):
    """Return `(best_move, best_value, cumulative_stats, info)`.

    When `time_limit_s` is set, the search can stop inside the current root
    iteration. The previous best move, or the best partial move from the current
    iteration, is kept so UI play does not freeze on expensive Hell positions.
    """
    tt = TranspositionTable()
    if killer_tbl is None and use_killer_moves:
        killer_tbl = KillerTable()
    if history_tbl is None and use_history_heuristic:
        history_tbl = HistoryTable()
    cumulative_stats = SearchStats()
    info: list[dict] = []

    deadline = time.perf_counter() + time_limit_s if time_limit_s else None
    best_move = None
    best_value = -math.inf

    for d in range(1, max(1, max_depth) + 1):
        if deadline is not None and time.perf_counter() >= deadline:
            break

        iter_stats = SearchStats()
        iter_start = time.perf_counter()
        root_key = (state_key(env.board), perspective)
        _, pv_move_uci = tt.probe(root_key, d, -math.inf, math.inf)

        moves = order_moves(env.board, env.legal_moves())
        if pv_move_uci:
            for i, m in enumerate(moves):
                if m.uci() == pv_move_uci:
                    if i != 0:
                        moves = [m] + moves[:i] + moves[i + 1:]
                    break

        iter_best_move = None
        iter_best_value = -math.inf
        iter_candidates = []
        timed_out = False

        for move in moves:
            if deadline is not None and time.perf_counter() >= deadline and iter_best_move is not None:
                timed_out = True
                break

            env.push(move)
            mm = alphabeta(
                env, d - 1, -math.inf, math.inf, False, evaluate, iter_stats, perspective,
                transposition=tt, killer_tbl=killer_tbl, history_tbl=history_tbl,
                use_quiescence=use_quiescence, q_max_depth=q_max_depth, ply=1,
            )
            env.pop()
            bonus = root_bonus_fn(move.uci()) if root_bonus_fn else 0.0
            score = mm + bonus
            iter_candidates.append({
                "move": move.uci(),
                "alphabeta_score": mm,
                "q_bonus": bonus,
                "final_score": score,
            })
            if score > iter_best_value:
                iter_best_value, iter_best_move = score, move

        if iter_best_move is not None:
            best_move = iter_best_move
            best_value = iter_best_value
            tt.store(root_key, d, iter_best_value, TTFlag.EXACT, best_move.uci())

        cumulative_stats.visited += iter_stats.visited
        cumulative_stats.pruned += iter_stats.pruned
        cumulative_stats.cache_hits += iter_stats.cache_hits
        cumulative_stats.q_visited += iter_stats.q_visited
        cumulative_stats.q_cutoffs += iter_stats.q_cutoffs

        info.append({
            "depth": d,
            "move": best_move.uci() if best_move else None,
            "value": best_value,
            "elapsed": time.perf_counter() - iter_start,
            "visited": iter_stats.visited,
            "pruned": iter_stats.pruned,
            "cache_hits": iter_stats.cache_hits,
            "timed_out": timed_out,
            "candidates": sorted(iter_candidates, key=lambda item: item["final_score"], reverse=True),
        })

        if timed_out or abs(best_value) > 90_000:
            break

    return best_move, best_value, cumulative_stats, info
