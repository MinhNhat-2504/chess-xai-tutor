"""Test tổng kết ván: accuracy, ACPL, giai đoạn, motif bị bỏ hở."""
import chess

from src.xai.game_summary import (
    format_summary_vi, game_phase, move_accuracy, summarize_game, win_chance_from_cp,
)

_ENDGAME_FEN = "8/5k2/8/8/8/3K4/4R3/8 b - - 0 40"


def _report(side, quality, loss, fen, san, opponent_motifs=()):
    return {
        "side": side,
        "quality": quality,
        "centipawn_loss": loss,
        "fen": fen,
        "move_san": san,
        "best_score": 50.0,
        "score": 50.0 - loss,
        "opponent_motifs": [{"kind": kind} for kind in opponent_motifs],
    }


def test_game_phase_classification():
    assert game_phase(chess.Board()) == "opening"
    middlegame = chess.Board("r1bqkbnr/pppppppp/2n5/8/8/2N5/PPPPPPPP/R1BQKBNR w KQkq - 4 15")
    assert game_phase(middlegame) == "middlegame"
    assert game_phase(chess.Board(_ENDGAME_FEN)) == "endgame"


def test_move_accuracy_decreases_with_win_chance_drop():
    perfect = move_accuracy(55.0, 55.0)
    sloppy = move_accuracy(55.0, 25.0)
    assert perfect > 99
    assert 0 <= sloppy < perfect
    assert win_chance_from_cp(0) == 50.0


def test_summarize_game_counts_and_phases():
    reports = [
        _report("white", "best", 0.0, chess.STARTING_FEN, "e4"),
        _report("white", "blunder", 400.0, chess.STARTING_FEN, "g4", opponent_motifs=("fork",)),
        _report("black", "mistake", 150.0, _ENDGAME_FEN, "Kg6"),
    ]
    summary = summarize_game(reports)

    assert summary["white"]["moves"] == 2
    assert summary["white"]["acpl"] == 200.0
    assert 0 < summary["white"]["accuracy"] < 100
    assert summary["white"]["counts"]["blunder"] == 1
    assert summary["white"]["allowed_motifs"] == {"fork": 1}
    assert summary["phase_errors"]["opening"]["white"] == 1
    assert summary["phase_errors"]["endgame"]["black"] == 1
    assert summary["worst_moves"][0]["label"] == "1.g4"
    assert summary["worst_moves"][0]["centipawn_loss"] == 400.0


def test_format_summary_lines_are_vietnamese_and_compact():
    reports = [
        _report("white", "blunder", 400.0, chess.STARTING_FEN, "g4", opponent_motifs=("fork",)),
        _report("black", "good", 20.0, chess.STARTING_FEN, "e5"),
    ]
    lines = format_summary_vi(summarize_game(reports))

    assert any(line.startswith("Trắng: accuracy") for line in lines)
    assert any("khai cuộc" in line for line in lines)
    assert any("1.g4" in line for line in lines)
    assert any("đòn đôi" in line for line in lines)
