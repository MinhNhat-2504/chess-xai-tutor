"""Smoke test cho helper của pygame_app — không khởi tạo cửa sổ thật.

`run_gui` import pygame BÊN TRONG hàm, nên import module này không yêu cầu
pygame đã cài. Test chỉ verify các helper coordinate mapping.
"""
import chess

from src.ui.pygame_app import (
    _candidate_move,
    _difficulty_button_rects,
    _legal_targets,
    _square_to_xy,
    _xy_to_square,
)


def test_a1_corner_white_perspective():
    """Khi human chơi trắng, a1 ở góc dưới-trái → (0, 7 * square_size)."""
    x, y = _square_to_xy(chess.A1, square_size=64, human_color=chess.WHITE)
    assert (x, y) == (0, 7 * 64)


def test_h8_corner_white_perspective():
    """h8 phải ở góc trên-phải."""
    x, y = _square_to_xy(chess.H8, square_size=64, human_color=chess.WHITE)
    assert (x, y) == (7 * 64, 0)


def test_round_trip_xy_white():
    for sq in (chess.A1, chess.E4, chess.H8, chess.D5):
        x, y = _square_to_xy(sq, 64, chess.WHITE)
        # Click vào TÂM ô
        sq2 = _xy_to_square(x + 32, y + 32, 64, chess.WHITE)
        assert sq2 == sq


def test_round_trip_xy_black():
    for sq in (chess.A1, chess.E4, chess.H8, chess.D5):
        x, y = _square_to_xy(sq, 64, chess.BLACK)
        sq2 = _xy_to_square(x + 32, y + 32, 64, chess.BLACK)
        assert sq2 == sq


def test_out_of_bounds_returns_none():
    assert _xy_to_square(-1, 0, 64, chess.WHITE) is None
    assert _xy_to_square(0, -1, 64, chess.WHITE) is None
    assert _xy_to_square(8 * 64, 0, 64, chess.WHITE) is None
    assert _xy_to_square(0, 8 * 64, 64, chess.WHITE) is None


def test_candidate_move_auto_promotes_to_queen():
    board = chess.Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    move = _candidate_move(board, chess.A7, chess.A8)
    assert move == chess.Move.from_uci("a7a8q")


def test_legal_targets_for_selected_piece():
    board = chess.Board()
    targets = _legal_targets(board, chess.E2)
    assert {chess.E3, chess.E4} <= targets


def test_difficulty_button_rects_are_centered_and_stable():
    rects = _difficulty_button_rects(600, 430, 3)
    assert len(rects) == 3
    assert all(rect[2] == 440 and rect[3] == 72 for rect in rects)
    assert all(rect[0] == 80 for rect in rects)
    assert rects[1][1] - rects[0][1] == 88
