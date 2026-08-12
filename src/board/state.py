"""Mã hóa trạng thái cho Q-table — Báo cáo mục 3.6.1.

LƯU Ý KHẢ THI (xem nhận xét outline): không gian trạng thái cờ vua quá lớn để
dùng key = FEN nguyên vẹn. Module này cung cấp hai dạng biểu diễn:
khóa FEN rút gọn cho Q-table và vector đặc trưng để mở rộng về sau.
"""
import chess


def state_key(board: chess.Board) -> str:
    """Khóa trạng thái rút gọn (bỏ số nước đi / cờ lặp) để tăng khả năng tái sử dụng."""
    parts = board.fen().split(" ")
    return " ".join(parts[:4])  # piece placement + lượt + nhập thành + en passant


def feature_vector(board: chess.Board) -> tuple[float, ...]:
    """Vector đặc trưng nhỏ gọn cho các hướng mở rộng Q-learning theo hàm xấp xỉ."""
    piece_counts = []
    for piece_type in (
        chess.PAWN,
        chess.KNIGHT,
        chess.BISHOP,
        chess.ROOK,
        chess.QUEEN,
    ):
        white_count = len(board.pieces(piece_type, chess.WHITE))
        black_count = len(board.pieces(piece_type, chess.BLACK))
        piece_counts.append(float(white_count - black_count))

    center_squares = (chess.D4, chess.E4, chess.D5, chess.E5)
    center_control = sum(
        len(board.attackers(chess.WHITE, square)) - len(board.attackers(chess.BLACK, square))
        for square in center_squares
    )
    turn = 1.0 if board.turn == chess.WHITE else -1.0
    castling = float(board.has_castling_rights(chess.WHITE)) - float(board.has_castling_rights(chess.BLACK))
    check = 1.0 if board.is_check() else 0.0

    mobility = float(_legal_move_count(board, chess.WHITE) - _legal_move_count(board, chess.BLACK))
    king_safety = float(_king_defenders(board, chess.WHITE) - _king_defenders(board, chess.BLACK))
    pawn_structure = float(_pawn_structure(board, chess.WHITE) - _pawn_structure(board, chess.BLACK))
    return (
        *piece_counts,
        float(center_control),
        turn,
        castling,
        check,
        mobility,
        king_safety,
        pawn_structure,
    )


def _legal_move_count(board: chess.Board, color: chess.Color) -> int:
    probe = board.copy(stack=False)
    probe.turn = color
    return probe.legal_moves.count()


def _king_defenders(board: chess.Board, color: chess.Color) -> int:
    king_square = board.king(color)
    if king_square is None:
        return 0
    return len(board.attackers(color, king_square))


def _pawn_structure(board: chess.Board, color: chess.Color) -> int:
    pawns = list(board.pieces(chess.PAWN, color))
    files = [chess.square_file(square) for square in pawns]
    doubled = sum(max(files.count(file) - 1, 0) for file in set(files))
    isolated = sum(1 for file in files if file - 1 not in files and file + 1 not in files)
    return len(pawns) - doubled - isolated
