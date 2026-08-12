"""Mô hình 2 — Minimax + Alpha-Beta. Báo cáo mục 3.8.2."""
import math
from .base_agent import BaseAgent
from ..search.alphabeta import alphabeta, SearchStats
from ..search.heuristics import KillerTable, HistoryTable
from ..search.move_ordering import order_moves
from ..search.transposition import TranspositionTable
from ..search.iterative_deepening import search_iterative_root
from ..evaluation.evaluator import evaluate


class AlphaBetaAgent(BaseAgent):
    def __init__(
        self,
        depth=4,
        use_transposition=True,
        use_quiescence=False,
        q_max_depth=6,
        use_iterative_deepening=False,
        time_limit_s=None,
        use_killer_moves=False,
        use_history_heuristic=False,
    ):
        self.depth = max(1, depth)
        self.use_transposition = use_transposition
        self.use_quiescence = use_quiescence
        self.q_max_depth = q_max_depth
        self.use_iterative_deepening = use_iterative_deepening
        self.time_limit_s = time_limit_s
        self.use_killer_moves = use_killer_moves
        self.use_history_heuristic = use_history_heuristic
        self.last_stats = None
        self.last_info = None  # iterative deepening: list[dict] per iteration
        self.last_candidates = []
        self.last_explanation = None

    def choose_move(self, env):
        if self.use_iterative_deepening:
            return self._choose_iterative(env)
        return self._choose_fixed(env)

    def _choose_fixed(self, env):
        perspective = env.board.turn
        stats = SearchStats()
        transposition = TranspositionTable() if self.use_transposition else None
        killer_tbl = KillerTable() if self.use_killer_moves else None
        history_tbl = HistoryTable() if self.use_history_heuristic else None
        best_move, best_val = None, -math.inf
        candidates = []
        for move in order_moves(env.board, env.legal_moves()):
            env.push(move)
            val = alphabeta(
                env,
                self.depth - 1,
                -math.inf,
                math.inf,
                False,
                evaluate,
                stats,
                perspective,
                transposition,
                killer_tbl=killer_tbl,
                history_tbl=history_tbl,
                use_quiescence=self.use_quiescence,
                q_max_depth=self.q_max_depth,
                ply=1,
            )
            env.pop()
            explanation = self._explanation(move, val)
            candidates.append(explanation)
            if val > best_val:
                best_val, best_move = val, move
                self.last_explanation = explanation
        self.last_stats = stats
        self.last_info = None
        self.last_candidates = sorted(candidates, key=lambda item: item["final_score"], reverse=True)
        return best_move

    def _choose_iterative(self, env):
        perspective = env.board.turn
        best_move, _, stats, info = search_iterative_root(
            env,
            self.depth,
            evaluate,
            perspective,
            time_limit_s=self.time_limit_s,
            use_quiescence=self.use_quiescence,
            q_max_depth=self.q_max_depth,
            use_killer_moves=self.use_killer_moves,
            use_history_heuristic=self.use_history_heuristic,
        )
        self.last_stats = stats
        self.last_info = info
        if info:
            self.last_candidates = info[-1].get("candidates", [])
            self.last_explanation = next(
                (item for item in self.last_candidates if best_move is not None and item["move"] == best_move.uci()),
                self.last_candidates[0] if self.last_candidates else None,
            )
        else:
            self.last_candidates = []
            self.last_explanation = None
        return best_move

    @staticmethod
    def _explanation(move, alphabeta_score):
        return {
            "move": move.uci(),
            "alphabeta_score": alphabeta_score,
            "final_score": alphabeta_score,
        }
