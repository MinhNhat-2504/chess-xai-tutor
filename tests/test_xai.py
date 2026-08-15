import chess

from src.evaluation.evaluator import evaluate, evaluate_breakdown
from src.xai import MoveExplainer


def test_breakdown_sums_to_existing_evaluator_score():
    board = chess.Board()
    breakdown = evaluate_breakdown(board, chess.WHITE)
    assert breakdown["total"] == evaluate(board, chess.WHITE)
    assert {"material_position", "mobility", "king_safety", "center_control"} <= set(breakdown)


def test_explainer_marks_queen_sacrifice_as_costly_at_shallow_depth():
    board = chess.Board("4k3/4p3/8/8/8/8/8/4Q2K w - - 0 1")
    report = MoveExplainer(depth=1, use_quiescence=True, use_stockfish=False).analyze_move(board, "e1e7")

    assert report["move_san"] == "Qxe7+"
    assert report["centipawn_loss"] > 500
    assert report["quality"] == "blunder"
    assert report["best_move_uci"] != "e1e7"
    assert "bắt tốt" in report["explanation_vi"].lower()


def test_explainer_reports_tactical_facts_and_pgn_style_game_rows():
    explainer = MoveExplainer(depth=1, use_stockfish=False)
    report = explainer.analyze_game([chess.Move.from_uci("e2e4"), chess.Move.from_uci("e7e5")])

    assert [row["ply"] for row in report] == [1, 2]
    assert report[0]["move_san"] == "e4"
    assert report[0]["top_candidates"]
    assert report[0]["method"]["depth"] == 1
