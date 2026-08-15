"""Test bộ nhận diện motif chiến thuật (luật thuần, không cần engine)."""
import chess
import pytest

from src.xai import MoveExplainer, detect_motifs


def _kinds(board_fen: str, move_uci: str) -> list[str]:
    motifs = detect_motifs(chess.Board(board_fen), chess.Move.from_uci(move_uci))
    return [m.kind for m in motifs]


def test_knight_fork_on_king_and_rook():
    # Nc7+ tấn công cùng lúc vua e8 và xe a8.
    kinds = _kinds("r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1", "d5c7")
    assert "fork" in kinds


def test_bishop_pin_against_king():
    # Bb5 ghim mã c6 vào vua e8.
    board = chess.Board("4k3/8/2n5/8/8/3B4/8/4K3 w - - 0 1")
    motifs = detect_motifs(board, chess.Move.from_uci("d3b5"))
    pins = [m for m in motifs if m.kind == "pin"]
    assert pins and "c6" in pins[0].squares


def test_rook_skewer_queen_then_rook():
    # Re1 xiên hậu e5; hậu chạy thì mất xe e8 phía sau.
    kinds = _kinds("4r3/8/8/4q3/8/8/8/R6K w - - 0 1", "a1e1")
    assert "skewer" in kinds


def test_discovered_check_when_knight_moves_off_diagonal():
    # Mã d2 rời chéo c1-g5, tượng c1 chiếu vua g5.
    kinds = _kinds("8/8/8/6k1/8/8/3N4/2B1K3 w - - 0 1", "d2b3")
    assert "discovered_check" in kinds


def test_back_rank_mate_detected():
    # Ra8# — vua g8 bị khoá bởi hàng tốt của chính mình.
    kinds = _kinds("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1", "a1a8")
    assert "back_rank_mate" in kinds


def test_quiet_opening_move_has_no_motifs():
    assert _kinds(chess.STARTING_FEN, "e2e4") == []


def test_motifs_flow_into_report_and_facts():
    board = chess.Board("r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1")
    explainer = MoveExplainer(depth=1, use_stockfish=False)
    report = explainer.analyze_move(board, "d5c7")

    assert any(m["kind"] == "fork" for m in report["motifs"])
    assert any("đòn đôi" in fact for fact in report["tactical_facts"])
    assert "đòn đôi" in report["explanation_vi"].lower()


def test_illegal_move_raises():
    with pytest.raises(ValueError):
        detect_motifs(chess.Board(), chess.Move.from_uci("e2e5"))
