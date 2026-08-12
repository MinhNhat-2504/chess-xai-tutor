"""Test tích hợp Stockfish oracle; tự skip khi máy chưa cài Stockfish."""
import chess
import pytest

from src.xai import MoveExplainer, StockfishOracle, find_stockfish

stockfish_missing = find_stockfish() is None
requires_stockfish = pytest.mark.skipif(stockfish_missing, reason="Chưa cài Stockfish")


@requires_stockfish
def test_oracle_scores_and_pv_for_opening_position():
    with StockfishOracle(depth=8, multipv=3) as oracle:
        result = oracle.analyze(chess.Board(), chess.Move.from_uci("e2e4"))

    assert result["name"].lower().startswith("stockfish")
    assert len(result["candidates"]) == 3
    assert result["played"]["move"] == "e2e4"
    assert result["played"]["pv"][0] == chess.Move.from_uci("e2e4")
    # 1.e4 là nước khai cuộc chuẩn: điểm không thể tệ hơn nước tốt nhất quá 45cp.
    assert result["candidates"][0]["score"] - result["played"]["score"] <= 45


@requires_stockfish
def test_explainer_with_stockfish_does_not_flag_e4():
    with MoveExplainer(engine_depth=10) as explainer:
        assert explainer.oracle is not None
        report = explainer.analyze_move(chess.Board(), "e2e4")

    assert report["quality"] in {"best", "good"}
    assert report["method"]["engine"].lower().startswith("stockfish")
    assert report["best_line_san"]
    assert 0 <= report["win_chance"] <= 100


@requires_stockfish
def test_explainer_with_stockfish_shows_refutation_for_blunder():
    board = chess.Board("4k3/4p3/8/8/8/8/8/4Q2K w - - 0 1")
    with MoveExplainer(engine_depth=10) as explainer:
        report = explainer.analyze_move(board, "e1e7")

    assert report["quality"] == "blunder"
    assert "Kxe7" in report["refutation_san"]
    assert "Kxe7" in report["explanation_vi"]


@requires_stockfish
def test_explainer_reports_motif_the_blunder_allows():
    # h3?? bỏ mặc ô c2: đen đáp Nc2+ tạo đòn đôi vua e1 + xe a1.
    board = chess.Board("4k3/8/8/8/1n6/8/7P/R3K3 w - - 0 1")
    with MoveExplainer(engine_depth=12) as explainer:
        report = explainer.analyze_move(board, "h2h3")

    assert report["quality"] in {"mistake", "blunder"}
    assert any(m["kind"] == "fork" for m in report["opponent_motifs"])
    assert "đòn đôi" in report["explanation_vi"]


@requires_stockfish
def test_suggest_move_with_stockfish_returns_line():
    with MoveExplainer(engine_depth=10) as explainer:
        suggestion = explainer.suggest_move(chess.Board())

    assert chess.Move.from_uci(suggestion["move_uci"]) in chess.Board().legal_moves
    assert suggestion["line_san"]
    assert suggestion["win_chance"] is not None


def test_suggest_move_fallback_returns_legal_move():
    explainer = MoveExplainer(depth=1, use_stockfish=False)
    suggestion = explainer.suggest_move(chess.Board())

    assert chess.Move.from_uci(suggestion["move_uci"]) in chess.Board().legal_moves
    assert suggestion["engine"].startswith("project")

    stalemate = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert explainer.suggest_move(stalemate) is None


def test_explainer_fallback_without_stockfish_keeps_legacy_shape():
    explainer = MoveExplainer(depth=1, use_stockfish=False)
    report = explainer.analyze_move(chess.Board(), "e2e4")

    assert explainer.oracle is None
    assert report["method"]["engine"].startswith("project Alpha-Beta")
    assert report["method"]["depth"] == 1
    assert "win_chance" not in report
    explainer.close()  # không có oracle vẫn gọi được
