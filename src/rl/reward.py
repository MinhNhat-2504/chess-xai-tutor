"""Phần thưởng đa tầng (Reward Shaping) — Báo cáo mục 3.6.2.

Tầng kết thúc ván (thắng/thua/hòa) + tầng định hình theo chênh lệch đánh giá vị trí.
"""
import chess


def terminal_reward(board: chess.Board, color: bool) -> float:
    if board.is_checkmate():
        return 1.0 if board.turn != color else -1.0
    return 0.0  # hòa


def shaping_reward(eval_before: float, eval_after: float, scale: float = 0.01) -> float:
    """Thưởng nhỏ khi nước đi làm vị trí tốt hơn theo hàm đánh giá."""
    return scale * (eval_after - eval_before)


def move_reward(board_before: chess.Board, move: chess.Move, board_after: chess.Board) -> float:
    """Thưởng nhỏ cho tín hiệu chiến thuật dễ hiểu trong báo cáo."""
    reward = 0.0
    if board_before.is_capture(move):
        reward += 0.05
    if move.promotion:
        reward += 0.10
    if board_after.is_check():
        reward += 0.03
    return reward
