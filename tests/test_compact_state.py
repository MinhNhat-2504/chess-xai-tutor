"""Test cho compact_state_key — Báo cáo mục 3.6.1 (mở rộng)."""
import chess

from src.board.compact_state import compact_state_key
from src.board.state import state_key


def test_compact_key_is_short_string():
    key = compact_state_key(chess.Board())
    assert isinstance(key, str)
    assert len(key) == 12     # 12 features → 12 ký tự
    assert key.isalpha()


def test_compact_key_collides_similar_positions():
    """Hai vị trí khác chút (ví dụ tốt e2 vs tốt e3) PHẢI khác state_key FEN,
    nhưng có thể giống compact key nếu feature_vector bucket như nhau."""
    board_a = chess.Board()  # vị trí khởi đầu
    board_b = chess.Board()
    board_b.push_uci("a2a3")  # nước nhỏ — feature vector gần như không đổi

    # Full FEN sẽ khác (turn đã đổi, fullmove number tăng, en passant rỗng vs có thể có)
    assert state_key(board_a) != state_key(board_b)

    # Compact sẽ KHÁC ít nhất ở turn (board_a: white-to-move, board_b: black-to-move)
    # Nhưng feature counts giữ nguyên → chỉ 1 vài chữ khác.
    key_a = compact_state_key(board_a)
    key_b = compact_state_key(board_b)
    diff = sum(1 for x, y in zip(key_a, key_b) if x != y)
    # Phải có khác biệt (turn) nhưng không khác toàn bộ
    assert 0 < diff < len(key_a)


def test_compact_key_distinguishes_material_difference():
    """Vị trí trắng dư hậu phải có key khác vị trí cân bằng."""
    even = chess.Board()
    plus_queen = chess.Board("rnbqkbnr/pppppppp/8/8/8/Q7/PPPPPPPP/RNB1KBNR w KQkq - 0 1")
    # trắng có hậu Q3 thêm — chênh lệch hậu = +1 → bucket khác

    key_even = compact_state_key(even)
    key_plus = compact_state_key(plus_queen)
    assert key_even != key_plus
