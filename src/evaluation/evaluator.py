"""Hàm đánh giá trạng thái — Báo cáo mục 2.6, 3.5.

Thành phần: vật chất, an toàn vua, kiểm soát trung tâm, khả năng chiếu, đe dọa.
"""
import chess
from .piece_tables import PIECE_VALUES, position_bonus


MATE_SCORE = 99999
CENTER_SQUARES = [chess.D4, chess.E4, chess.D5, chess.E5]
EXTENDED_CENTER = [
    chess.C3, chess.D3, chess.E3, chess.F3,
    chess.C4, chess.F4, chess.C5, chess.F5,
    chess.C6, chess.D6, chess.E6, chess.F6,
]


def _terminal_score(board: chess.Board) -> float | None:
    if board.is_checkmate():
        winner = not board.turn
        return MATE_SCORE if winner == chess.WHITE else -MATE_SCORE
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return 0.0
    return None


def _mobility_score(board: chess.Board) -> float:
    white_probe = board.copy(stack=False)
    black_probe = board.copy(stack=False)
    white_probe.turn = chess.WHITE
    black_probe.turn = chess.BLACK
    white_moves = white_probe.legal_moves.count()
    black_moves = black_probe.legal_moves.count()
    return 0.8 * (white_moves - black_moves)


def _king_safety(board: chess.Board) -> float:
    score = 0.0
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        king_square = board.king(color)
        if king_square is None:
            continue
        attackers = len(board.attackers(not color, king_square))
        defenders = len(board.attackers(color, king_square))
        score += sign * (4.0 * defenders - 12.0 * attackers)
    return score


def _center_control(board: chess.Board) -> float:
    score = 0.0
    for square in CENTER_SQUARES:
        score += 8.0 * (len(board.attackers(chess.WHITE, square)) - len(board.attackers(chess.BLACK, square)))
    for square in EXTENDED_CENTER:
        score += 2.0 * (len(board.attackers(chess.WHITE, square)) - len(board.attackers(chess.BLACK, square)))
    return score


def _pawn_structure_score(board: chess.Board) -> float:
    score = 0.0
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        pawns = list(board.pieces(chess.PAWN, color))
        files = [chess.square_file(square) for square in pawns]
        doubled = sum(max(files.count(file) - 1, 0) for file in set(files))
        isolated = sum(1 for file in files if file - 1 not in files and file + 1 not in files)
        passed = 0
        for square in pawns:
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            enemy_pawns = board.pieces(chess.PAWN, not color)
            blocker_files = {file - 1, file, file + 1}
            if color == chess.WHITE:
                ahead = [sq for sq in enemy_pawns if chess.square_rank(sq) > rank]
            else:
                ahead = [sq for sq in enemy_pawns if chess.square_rank(sq) < rank]
            if not any(chess.square_file(sq) in blocker_files for sq in ahead):
                passed += 1
        score += sign * (12.0 * passed - 8.0 * doubled - 6.0 * isolated)
    return score


def _development_score(board: chess.Board) -> float:
    score = 0.0
    home_squares = {
        chess.WHITE: {chess.B1, chess.G1, chess.C1, chess.F1},
        chess.BLACK: {chess.B8, chess.G8, chess.C8, chess.F8},
    }
    for color, sign in ((chess.WHITE, 1), (chess.BLACK, -1)):
        undeveloped = 0
        for square in home_squares[color]:
            piece = board.piece_at(square)
            if piece and piece.color == color and piece.piece_type in (chess.KNIGHT, chess.BISHOP):
                undeveloped += 1
        score -= sign * 7.0 * undeveloped
        if not board.has_castling_rights(color):
            king_square = board.king(color)
            if king_square in (chess.G1, chess.C1, chess.G8, chess.C8):
                score += sign * 18.0
    return score


def _threat_score(board: chess.Board) -> float:
    score = 0.0
    for square, piece in board.piece_map().items():
        attackers = board.attackers(not piece.color, square)
        defenders = board.attackers(piece.color, square)
        if attackers and not defenders:
            sign = -1 if piece.color == chess.WHITE else 1
            score += sign * 0.08 * PIECE_VALUES[piece.piece_type]
    return score


def evaluate(board: chess.Board, perspective: chess.Color = chess.WHITE) -> float:
    """Trả điểm theo góc nhìn `perspective`: dương là tốt cho bên đó."""
    return evaluate_breakdown(board, perspective)["total"]


def evaluate_breakdown(board: chess.Board, perspective: chess.Color = chess.WHITE) -> dict[str, float]:
    """Phân rã điểm đánh giá theo từng yếu tố, từ góc nhìn ``perspective``.

    Tổng các giá trị trả về luôn bằng :func:`evaluate`.  Hàm này dành cho lớp
    XAI: thay vì chỉ nói một nước đi có điểm ``+42``, giao diện có thể cho biết
    điểm đó đến từ vật chất, an toàn vua, trung tâm, hay cấu trúc tốt.
    """
    terminal = _terminal_score(board)
    if terminal is not None:
        score = terminal if perspective == chess.WHITE else -terminal
        return {"terminal": score, "total": score}

    material = 0.0
    for sq, piece in board.piece_map().items():
        val = PIECE_VALUES[piece.piece_type] + position_bonus(piece, sq)
        material += val if piece.color == chess.WHITE else -val
    raw = {
        "material_position": material,
        "mobility": _mobility_score(board),
        "king_safety": _king_safety(board),
        "center_control": _center_control(board),
        "pawn_structure": _pawn_structure_score(board),
        "development": _development_score(board),
        "threats": _threat_score(board),
        "check_pressure": 0.0,
    }
    if board.is_check():
        raw["check_pressure"] = -35.0 if board.turn == chess.WHITE else 35.0

    sign = 1.0 if perspective == chess.WHITE else -1.0
    breakdown = {name: value * sign for name, value in raw.items()}
    breakdown["total"] = sum(breakdown.values())
    return breakdown
