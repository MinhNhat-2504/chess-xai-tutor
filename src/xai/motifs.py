"""Nhận diện motif chiến thuật có tên cho lớp XAI.

Người học cờ nghe "đòn đôi", "ghim", "đòn xiên" — không nghe "mất 250
centipawn". Module này phát hiện các motif kinh điển bằng luật cờ thuần
(python-chess), độc lập với engine, nên dùng được cả khi có lẫn không có
Stockfish và không bao giờ "bịa" motif không kiểm chứng được:

* **fork** — đòn đôi: một quân tấn công cùng lúc ≥2 mục tiêu giá trị.
* **pin** — ghim: quân đối thủ không thể di chuyển vì sẽ lộ vua.
* **skewer** — đòn xiên: quân giá trị cao bị tấn công, chạy thì lộ quân sau.
* **discovered_attack / discovered_check** — đòn mở: quân rời chỗ mở đường
  cho quân dài phía sau tấn công/chiếu.
* **back_rank_mate** — chiếu hết tầng cuối.

Mỗi motif kèm mô tả tiếng Việt sẵn để đưa thẳng vào câu giải thích.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import chess

from ..evaluation.piece_tables import PIECE_VALUES


PIECE_NAMES_VI = {
    chess.PAWN: "tốt", chess.KNIGHT: "mã", chess.BISHOP: "tượng",
    chess.ROOK: "xe", chess.QUEEN: "hậu", chess.KING: "vua",
}

MOTIF_LABELS_VI = {
    "fork": "đòn đôi",
    "pin": "ghim quân",
    "skewer": "đòn xiên",
    "discovered_attack": "đòn mở",
    "discovered_check": "đòn mở chiếu",
    "back_rank_mate": "chiếu hết tầng cuối",
}

_DIAG_DIRECTIONS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
_LINE_DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))
_SLIDERS = {chess.BISHOP, chess.ROOK, chess.QUEEN}


@dataclass(frozen=True)
class Motif:
    kind: str
    label_vi: str
    description_vi: str
    squares: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["squares"] = list(self.squares)
        return data


def detect_motifs(board: chess.Board, move: chess.Move) -> list[Motif]:
    """Liệt kê motif mà ``move`` tạo ra trên ``board`` (chưa push nước đi)."""
    board_before = board.copy(stack=False)
    if move not in board_before.legal_moves:
        raise ValueError(f"Illegal move for this position: {move.uci()}")
    color = board_before.turn
    board_after = board_before.copy(stack=False)
    board_after.push(move)

    motifs: list[Motif] = []
    mate = _back_rank_mate(board_after, color)
    if mate:
        motifs.append(mate)
    fork = _fork(board_after, color, move.to_square)
    if fork:
        motifs.append(fork)
    motifs.extend(_discovered_attacks(board_before, board_after, color, move))
    motifs.extend(_new_pins(board_before, board_after, color))
    motifs.extend(_skewers(board_after, color, move.to_square))
    return motifs


def _piece_label(board: chess.Board, square: int) -> str:
    piece = board.piece_at(square)
    name = PIECE_NAMES_VI[piece.piece_type] if piece else "ô"
    return f"{name} {chess.square_name(square)}"


def _slider_directions(piece_type: int) -> tuple[tuple[int, int], ...]:
    if piece_type == chess.BISHOP:
        return _DIAG_DIRECTIONS
    if piece_type == chess.ROOK:
        return _LINE_DIRECTIONS
    return _DIAG_DIRECTIONS + _LINE_DIRECTIONS


def _scan_ray(board: chess.Board, start: int, df: int, dr: int):
    """Duyệt từng ô theo một hướng, trả (ô, quân-tại-ô hoặc None)."""
    f, r = chess.square_file(start) + df, chess.square_rank(start) + dr
    while 0 <= f < 8 and 0 <= r < 8:
        square = chess.square(f, r)
        yield square, board.piece_at(square)
        f, r = f + df, r + dr


def _on_open_line(slider_sq: int, vacated_sq: int, target_sq: int) -> bool:
    """``vacated_sq`` có nằm chắn giữa ``slider_sq`` và ``target_sq`` không."""
    df = chess.square_file(target_sq) - chess.square_file(slider_sq)
    dr = chess.square_rank(target_sq) - chess.square_rank(slider_sq)
    if df != 0 and dr != 0 and abs(df) != abs(dr):
        return False  # không thẳng hàng/chéo
    step_f = (df > 0) - (df < 0)
    step_r = (dr > 0) - (dr < 0)
    f = chess.square_file(slider_sq) + step_f
    r = chess.square_rank(slider_sq) + step_r
    while (f, r) != (chess.square_file(target_sq), chess.square_rank(target_sq)):
        if chess.square(f, r) == vacated_sq:
            return True
        f, r = f + step_f, r + step_r
    return False


def _fork(board_after: chess.Board, color: chess.Color, to_sq: int) -> Motif | None:
    attacker = board_after.piece_at(to_sq)
    if attacker is None:
        return None
    targets = []
    for square in board_after.attacks(to_sq):
        target = board_after.piece_at(square)
        if target is None or target.color == color:
            continue
        valuable = (
            target.piece_type == chess.KING
            or PIECE_VALUES[target.piece_type] > PIECE_VALUES[attacker.piece_type]
            or not board_after.attackers(target.color, square)
        )
        if valuable:
            targets.append(square)
    if len(targets) < 2:
        return None
    # Quân tạo đòn đôi bị bắt trắng ngay thì không tính là đòn đôi thật.
    if board_after.attackers(not color, to_sq) and not board_after.attackers(color, to_sq):
        return None
    target_text = " và ".join(_piece_label(board_after, sq) for sq in targets[:3])
    return Motif(
        kind="fork",
        label_vi=MOTIF_LABELS_VI["fork"],
        description_vi=f"đòn đôi: {_piece_label(board_after, to_sq)} tấn công cùng lúc {target_text}",
        squares=tuple(chess.square_name(sq) for sq in (to_sq, *targets[:3])),
    )


def _new_pins(board_before: chess.Board, board_after: chess.Board, color: chess.Color) -> list[Motif]:
    motifs = []
    for square, piece in board_after.piece_map().items():
        if piece.color == color or piece.piece_type == chess.KING:
            continue
        if not board_after.is_pinned(piece.color, square):
            continue
        already_pinned = (
            board_before.piece_at(square) == piece
            and board_before.is_pinned(piece.color, square)
        )
        if already_pinned:
            continue
        motifs.append(Motif(
            kind="pin",
            label_vi=MOTIF_LABELS_VI["pin"],
            description_vi=(
                f"ghim quân: {_piece_label(board_after, square)} bị ghim vào vua, "
                "không thể rời vị trí"
            ),
            squares=(chess.square_name(square),),
        ))
    return motifs


def _skewers(board_after: chess.Board, color: chess.Color, to_sq: int) -> list[Motif]:
    attacker = board_after.piece_at(to_sq)
    if attacker is None or attacker.piece_type not in _SLIDERS:
        return []
    motifs = []
    for df, dr in _slider_directions(attacker.piece_type):
        front = back = None
        for square, piece in _scan_ray(board_after, to_sq, df, dr):
            if piece is None:
                continue
            if front is None:
                front = (square, piece)
                if piece.color == color:
                    break  # đường bị quân mình chặn
                continue
            back = (square, piece)
            break
        if not front or not back:
            continue
        front_sq, front_piece = front
        back_sq, back_piece = back
        if front_piece.color == color or back_piece.color == color:
            continue
        if back_piece.piece_type == chess.KING:
            continue  # vua đứng sau là ghim, đã xử lý ở _new_pins
        front_value = PIECE_VALUES[front_piece.piece_type]
        back_value = PIECE_VALUES[back_piece.piece_type]
        forced = front_piece.piece_type == chess.KING or (
            front_value > PIECE_VALUES[attacker.piece_type] and front_value > back_value
        )
        worthwhile = (
            back_value >= PIECE_VALUES[chess.KNIGHT]
            or not board_after.attackers(not color, back_sq)
        )
        if forced and worthwhile:
            motifs.append(Motif(
                kind="skewer",
                label_vi=MOTIF_LABELS_VI["skewer"],
                description_vi=(
                    f"đòn xiên: {_piece_label(board_after, to_sq)} tấn công "
                    f"{_piece_label(board_after, front_sq)}; nếu chạy sẽ mất "
                    f"{_piece_label(board_after, back_sq)} phía sau"
                ),
                squares=(
                    chess.square_name(to_sq),
                    chess.square_name(front_sq),
                    chess.square_name(back_sq),
                ),
            ))
    return motifs


def _discovered_attacks(
    board_before: chess.Board,
    board_after: chess.Board,
    color: chess.Color,
    move: chess.Move,
) -> list[Motif]:
    motifs = []
    for slider_sq, piece in board_after.piece_map().items():
        if piece.color != color or piece.piece_type not in _SLIDERS:
            continue
        if slider_sq == move.to_square:
            continue  # quân vừa đi tự tấn công thì không phải "đòn mở"
        attacked_before = (
            board_before.attacks(slider_sq)
            if board_before.piece_at(slider_sq) == piece
            else chess.SquareSet()
        )
        for target_sq in board_after.attacks(slider_sq):
            target = board_after.piece_at(target_sq)
            if target is None or target.color == color or target_sq in attacked_before:
                continue
            if not _on_open_line(slider_sq, move.from_square, target_sq):
                continue
            if target.piece_type == chess.KING:
                motifs.append(Motif(
                    kind="discovered_check",
                    label_vi=MOTIF_LABELS_VI["discovered_check"],
                    description_vi=(
                        f"đòn mở chiếu: {_piece_label(board_after, slider_sq)} "
                        f"chiếu vua khi quân rời {chess.square_name(move.from_square)}"
                    ),
                    squares=(chess.square_name(slider_sq), chess.square_name(target_sq)),
                ))
            elif (
                PIECE_VALUES[target.piece_type] >= PIECE_VALUES[chess.ROOK]
                or not board_after.attackers(target.color, target_sq)
            ):
                motifs.append(Motif(
                    kind="discovered_attack",
                    label_vi=MOTIF_LABELS_VI["discovered_attack"],
                    description_vi=(
                        f"đòn mở: {_piece_label(board_after, slider_sq)} "
                        f"tấn công {_piece_label(board_after, target_sq)} khi đường được mở"
                    ),
                    squares=(chess.square_name(slider_sq), chess.square_name(target_sq)),
                ))
    return motifs


def _back_rank_mate(board_after: chess.Board, color: chess.Color) -> Motif | None:
    if not board_after.is_checkmate():
        return None
    king_sq = board_after.king(not color)
    back_rank = 0 if (not color) == chess.WHITE else 7
    if king_sq is None or chess.square_rank(king_sq) != back_rank:
        return None
    checkers = list(board_after.checkers())
    on_rank_heavy = [
        sq for sq in checkers
        if chess.square_rank(sq) == back_rank
        and board_after.piece_at(sq).piece_type in {chess.ROOK, chess.QUEEN}
    ]
    if not on_rank_heavy:
        return None
    return Motif(
        kind="back_rank_mate",
        label_vi=MOTIF_LABELS_VI["back_rank_mate"],
        description_vi=(
            "chiếu hết tầng cuối: vua bị khoá ở hàng cuối "
            f"và {_piece_label(board_after, on_rank_heavy[0])} kết thúc ván cờ"
        ),
        squares=(chess.square_name(on_rank_heavy[0]), chess.square_name(king_sq)),
    )
