"""Minimax thuần túy — Mô hình 1. Báo cáo mục 2.3, 3.8.1."""
import math


def minimax(env, depth: int, maximizing: bool, evaluate, perspective) -> float:
    if depth == 0 or env.is_terminal():
        return evaluate(env.board, perspective)
    if maximizing:
        best = -math.inf
        for move in env.legal_moves():
            env.push(move)
            best = max(best, minimax(env, depth - 1, False, evaluate, perspective))
            env.pop()
        return best
    else:
        best = math.inf
        for move in env.legal_moves():
            env.push(move)
            best = min(best, minimax(env, depth - 1, True, evaluate, perspective))
            env.pop()
        return best
