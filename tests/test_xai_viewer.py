import chess
import chess.pgn

from src.ui.xai_viewer import game_positions, next_error_index, read_pgn


def test_read_pgn_and_build_positions(tmp_path):
    path = tmp_path / "game.pgn"
    path.write_text('[Event "demo"]\n\n1. e4 e5 *\n', encoding="utf-8")

    game = read_pgn(path)
    initial, moves, positions = game_positions(game)

    assert initial == chess.Board()
    assert [move.uci() for move in moves] == ["e2e4", "e7e5"]
    assert len(positions) == 3
    assert positions[-1].piece_at(chess.E5).piece_type == chess.PAWN


def test_next_error_index_skips_good_moves_and_returns_board_position():
    reports = {
        0: {"quality": "best"},
        1: {"quality": "good"},
        2: {"quality": "mistake"},
    }
    assert next_error_index(reports, current=0, total=3) == 3
    assert next_error_index(reports, current=3, total=3) is None
