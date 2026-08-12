"""State representation rút gọn cho Q-Learning — Báo cáo mục 3.6.1 (mở rộng).

Vấn đề: `state_key` (FEN rút gọn) có không gian ~10^46. Q-table gần như
không bao giờ revisit cùng state ngoài opening → bị "state explosion".

Giải pháp: dùng `feature_vector` (vốn đã có sẵn nhưng chưa được sử dụng)
rồi BUCKET từng feature vào một số rời rạc → chuỗi canonical ngắn. Hai vị
trí khác nhau nhưng có cùng "tình thế đại lượng" sẽ chia sẻ Q-value.

ĐÁNH ĐỔI: lossy — một số tinh tế chiến thuật bị mất. Vì vậy để default vẫn
là `full` trong `config.yaml`; `compact` chỉ dùng cho thí nghiệm ablation.
"""
import chess

from .state import feature_vector


def _bucket(value: float, edges: tuple[float, ...]) -> int:
    """Trả index của bucket: số edge nhỏ hơn `value`."""
    for i, e in enumerate(edges):
        if value < e:
            return i
    return len(edges)


# Edges cho từng chiều feature_vector (giữ ngắn để mã hoá nhanh).
# 5 chiều đầu là chênh lệch quân (pawn/knight/bishop/rook/queen).
_PIECE_EDGES = (-2.5, -0.5, 0.5, 2.5)         # 5 bucket: -3 / -1..-1 / 0 / +1..+2 / +3+
_CENTER_EDGES = (-4.0, -1.0, 1.0, 4.0)
_TURN_EDGES = (0.0,)                          # 2 bucket: black=0, white=1
_CASTLING_EDGES = (-0.5, 0.5)                 # 3 bucket
_CHECK_EDGES = (0.5,)                         # 2 bucket
_MOBILITY_EDGES = (-15.0, -3.0, 3.0, 15.0)
_KING_DEF_EDGES = (-2.0, 0.0, 2.0)
_PAWN_STRUCT_EDGES = (-3.0, 0.0, 3.0)

_ALL_EDGES = (
    _PIECE_EDGES, _PIECE_EDGES, _PIECE_EDGES, _PIECE_EDGES, _PIECE_EDGES,
    _CENTER_EDGES, _TURN_EDGES, _CASTLING_EDGES, _CHECK_EDGES,
    _MOBILITY_EDGES, _KING_DEF_EDGES, _PAWN_STRUCT_EDGES,
)


def compact_state_key(board: chess.Board) -> str:
    """Tạo string canonical từ `feature_vector` đã được bucket hoá.

    Mỗi feature → 1 ký tự (chữ cái hoa). Tổng = chuỗi có độ dài cố định.
    """
    fv = feature_vector(board)
    # feature_vector và _ALL_EDGES đều có 12 phần tử (đã khớp).
    parts = [chr(ord("A") + _bucket(value, edges)) for value, edges in zip(fv, _ALL_EDGES)]
    return "".join(parts)
