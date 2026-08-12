import chess

from scripts.evaluate import OPENING_FENS


def test_opening_suite_fens_are_valid():
    assert "start" in OPENING_FENS
    assert len(OPENING_FENS) >= 5
    for name, fen in OPENING_FENS.items():
        if fen is None:
            continue
        board = chess.Board(fen)
        assert board.is_valid(), name
