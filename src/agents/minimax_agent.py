"""Mô hình 1 — Minimax cơ bản. Báo cáo mục 3.8.1."""
import math
from .base_agent import BaseAgent
from ..search.minimax import minimax
from ..evaluation.evaluator import evaluate


class MinimaxAgent(BaseAgent):
    def __init__(self, depth=3):
        self.depth = max(1, depth)
        self.last_candidates = []
        self.last_explanation = None

    def choose_move(self, env):
        perspective = env.board.turn
        best_move, best_val = None, -math.inf
        candidates = []
        for move in env.legal_moves():
            env.push(move)
            val = minimax(env, self.depth - 1, False, evaluate, perspective)
            env.pop()
            explanation = {
                "move": move.uci(),
                "minimax_score": val,
                "final_score": val,
            }
            candidates.append(explanation)
            if val > best_val:
                best_val, best_move = val, move
                self.last_explanation = explanation
        self.last_candidates = sorted(candidates, key=lambda item: item["final_score"], reverse=True)
        return best_move
