"""Quiescence Search — Báo cáo mục 2.4.3.

Khắc phục **horizon effect**: ở leaf của alpha-beta (depth=0), nếu chỉ trả
`evaluate(board)` ngay, AI có thể đánh giá sai khi position còn nước "ồn"
(capture, promotion). Quiescence kéo dài tìm kiếm THÊM trên các nước ồn cho
đến khi vị trí đã "yên" mới gọi `evaluate`.

Cơ chế *stand-pat*: giả sử bên có lượt không bắt buộc phải đi nước ồn — họ có
thể "đứng yên" và lấy chính `evaluate(board)`. Đây là cận dưới (cho bên đi)
cho giá trị quiescence, dùng để cắt tỉa α-β trong quiescence.

`maximizing` tự suy từ `env.board.turn == perspective` để khớp với convention
của `alphabeta`.
"""
import math

from .move_ordering import order_moves


def _noisy_moves(board, ply: int):
    """Captures + promotions; có thêm checks ở ply đầu của quiescence."""
    out = []
    for m in board.legal_moves:
        if board.is_capture(m) or m.promotion:
            out.append(m)
        elif ply == 0 and board.gives_check(m):
            out.append(m)
    return out


def quiescence(env, alpha: float, beta: float, evaluate, stats, perspective,
               ply: int = 0, q_max_depth: int = 6) -> float:
    """Trả giá trị quiescence từ góc nhìn `perspective`."""
    stats.q_visited += 1

    # Terminal: trả luôn (mate / stalemate đã có giá trị xác định)
    if env.is_terminal():
        return evaluate(env.board, perspective)

    stand_pat = evaluate(env.board, perspective)
    maximizing = (env.board.turn == perspective)

    # Cap độ sâu để tránh bùng nổ chuỗi bắt đổi
    if ply >= q_max_depth:
        return stand_pat

    if maximizing:
        if stand_pat >= beta:
            stats.q_cutoffs += 1
            return stand_pat
        if stand_pat > alpha:
            alpha = stand_pat
    else:
        if stand_pat <= alpha:
            stats.q_cutoffs += 1
            return stand_pat
        if stand_pat < beta:
            beta = stand_pat

    noisy = _noisy_moves(env.board, ply)
    if not noisy:
        return stand_pat

    moves = order_moves(env.board, noisy)

    if maximizing:
        value = stand_pat
        for move in moves:
            env.push(move)
            child = quiescence(env, alpha, beta, evaluate, stats, perspective, ply + 1, q_max_depth)
            env.pop()
            if child > value:
                value = child
            alpha = max(alpha, value)
            if alpha >= beta:
                stats.q_cutoffs += 1
                break
        return value
    else:
        value = stand_pat
        for move in moves:
            env.push(move)
            child = quiescence(env, alpha, beta, evaluate, stats, perspective, ply + 1, q_max_depth)
            env.pop()
            if child < value:
                value = child
            beta = min(beta, value)
            if beta <= alpha:
                stats.q_cutoffs += 1
                break
        return value
