"""Smoke test cho module analytics.plots — chỉ kiểm tra render không lỗi."""
import csv
import json
import pytest

from src.analytics.plots import (
    plot_training_curves,
    plot_evaluation_summary,
    plot_node_counts,
)


@pytest.fixture
def matplotlib_available():
    pytest.importorskip("matplotlib")


def test_training_curves_renders(tmp_path, matplotlib_available):
    history = tmp_path / "history.csv"
    fieldnames = ["game", "result", "moves", "total_reward", "q_size", "epsilon", "replay_size", "replay_updates"]
    with history.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for g in range(1, 21):
            w.writerow({
                "game": g, "result": "1/2-1/2", "moves": 30, "total_reward": 0.1 * g,
                "q_size": g * 100, "epsilon": 0.2 * (0.999 ** g), "replay_size": g * 30,
                "replay_updates": 4,
            })
    out = plot_training_curves(history, tmp_path / "fig")
    assert out.exists()
    assert out.suffix == ".png"


def test_evaluation_summary_renders(tmp_path, matplotlib_available):
    summary = {
        "minimax": {"wins": 5, "losses": 15, "draws": 0, "avg_time_per_move": 0.01,
                    "avg_nodes_visited_per_move": 100, "avg_nodes_pruned_per_move": 0},
        "alphabeta": {"wins": 12, "losses": 5, "draws": 3, "avg_time_per_move": 0.05,
                      "avg_nodes_visited_per_move": 200, "avg_nodes_pruned_per_move": 50},
        "hybrid": {"wins": 15, "losses": 3, "draws": 2, "avg_time_per_move": 0.06,
                   "avg_nodes_visited_per_move": 250, "avg_nodes_pruned_per_move": 60},
    }
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")

    out = plot_evaluation_summary(path, tmp_path / "fig")
    assert out.exists()
    out2 = plot_node_counts(path, tmp_path / "fig")
    assert out2.exists()
