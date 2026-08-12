"""Sắp xếp nước đi (Move Ordering) — Báo cáo mục 2.4.2.

Ưu tiên ăn quân (MVV-LVA), phong cấp, chiếu để Alpha-Beta cắt tỉa sớm hơn.
Bản nâng cấp thêm killer-moves & history heuristic (mục 2.4.2 mở rộng):
- Killer move (quiet move từng gây β-cutoff tại cùng ply) được nâng điểm cao.
- History score (cộng dồn `depth²`) làm tiebreaker cho các quiet move.

Default args giữ tương thích ngược: nếu không truyền killers/history,
hành vi y hệt bản đồ án gốc.
"""
import chess

from ..evaluation.piece_tables import PIECE_VALUES


def order_moves(board: chess.Board, moves, killers=(), history=None):
    killers = tuple(killers)

    def score(m: chess.Move) -> int:
        s = 0
        attacker = board.piece_at(m.from_square)
        is_capture = board.is_capture(m)
        if is_capture:
            victim = board.piece_at(m.to_square)
            if victim is None and board.is_en_passant(m):
                victim = chess.Piece(chess.PAWN, not board.turn)
            victim_value = PIECE_VALUES.get(victim.piece_type, 0) if victim else 0
            attacker_value = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
            s += 10_000 + 10 * victim_value - attacker_value
        if m.promotion:
            s += 8_000 + PIECE_VALUES.get(m.promotion, 0)
        if board.gives_check(m):
            s += 2_000
        if board.is_castling(m):
            s += 500
        if not is_capture and killers and m.uci() in killers:
            # Killer chỉ áp dụng cho quiet move (không-ăn-quân)
            s += 1_500
        if not is_capture and history is not None:
            # Cap history bonus để không chèn ép captures/promotions
            s += min(history.score(board, m), 1_000)
        return s

    return sorted(moves, key=score, reverse=True)
