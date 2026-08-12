"""Sinh biểu đồ phân tích cho báo cáo — mục 4.6.

Đọc CSV/JSON do `scripts/train.py` & `scripts/evaluate.py` xuất ra, vẽ:
- `plot_training_curves`: |Q|, mean|Q|, epsilon, total_reward theo số ván.
- `plot_evaluation_summary`: win/loss/draw + thời gian/nước cho 3 model.
- `plot_node_counts`: nodes_visited / nodes_pruned trung bình mỗi nước.

Module import matplotlib lazily — nếu matplotlib không có, các hàm sẽ
raise ImportError với thông điệp rõ ràng (không phá vỡ test khác).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path


def _setup_matplotlib():
    import matplotlib
    matplotlib.use("Agg")  # headless: không cần display
    import matplotlib.pyplot as plt
    return plt


def _read_history_csv(path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plot_training_curves(history_csv, out_dir) -> Path:
    """Vẽ 4 đường: q_size, mean|Q| ước lượng qua chuỗi reward, epsilon,
    total_reward theo số ván. Lưu PNG vào `out_dir/training_curves.png`."""
    plt = _setup_matplotlib()
    rows = _read_history_csv(history_csv)
    if not rows:
        raise ValueError(f"Empty history CSV: {history_csv}")

    games = [int(r["game"]) for r in rows]
    q_size = [int(r["q_size"]) for r in rows]
    epsilon = [float(r["epsilon"]) for r in rows]
    total_reward = [float(r["total_reward"]) for r in rows]
    replay_size = [int(r.get("replay_size", 0)) for r in rows]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes[0, 0].plot(games, q_size, color="tab:blue")
    axes[0, 0].set_title("|Q| theo số ván self-play")
    axes[0, 0].set_xlabel("game"); axes[0, 0].set_ylabel("|Q|"); axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(games, epsilon, color="tab:orange")
    axes[0, 1].set_title("Epsilon decay (Exploration → Exploitation)")
    axes[0, 1].set_xlabel("game"); axes[0, 1].set_ylabel("ε"); axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].plot(games, total_reward, color="tab:green", alpha=0.6, label="raw")
    if len(total_reward) >= 10:
        window = max(1, len(total_reward) // 20)
        smoothed = [
            sum(total_reward[max(0, i - window):i + 1]) / (min(i, window) + 1)
            for i in range(len(total_reward))
        ]
        axes[1, 0].plot(games, smoothed, color="darkgreen", label=f"MA(window={window})")
    axes[1, 0].set_title("Total reward mỗi ván")
    axes[1, 0].set_xlabel("game"); axes[1, 0].set_ylabel("reward"); axes[1, 0].legend(); axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].plot(games, replay_size, color="tab:red")
    axes[1, 1].set_title("Replay buffer size")
    axes[1, 1].set_xlabel("game"); axes[1, 1].set_ylabel("transitions"); axes[1, 1].grid(True, alpha=0.3)

    fig.tight_layout()
    out_path = out_dir / "training_curves.png"
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_evaluation_summary(summary_json, out_dir) -> Path:
    """Bar chart win/loss/draw cho mỗi model + thời gian trung bình mỗi nước."""
    plt = _setup_matplotlib()
    with Path(summary_json).open(encoding="utf-8") as f:
        summary = json.load(f)
    if not summary:
        raise ValueError(f"Empty summary: {summary_json}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    names = list(summary.keys())
    wins = [summary[n].get("wins", 0) for n in names]
    losses = [summary[n].get("losses", 0) for n in names]
    draws = [summary[n].get("draws", 0) for n in names]
    avg_time = [summary[n].get("avg_time_per_move", 0.0) for n in names]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    x = list(range(len(names)))
    width = 0.25
    axes[0].bar([i - width for i in x], wins, width=width, label="Win", color="tab:green")
    axes[0].bar(x, draws, width=width, label="Draw", color="tab:gray")
    axes[0].bar([i + width for i in x], losses, width=width, label="Loss", color="tab:red")
    axes[0].set_xticks(x); axes[0].set_xticklabels(names)
    axes[0].set_title("Kết quả thi đấu vòng tròn"); axes[0].set_ylabel("số ván")
    axes[0].legend(); axes[0].grid(True, alpha=0.3, axis="y")

    axes[1].bar(names, avg_time, color="tab:purple")
    axes[1].set_title("Thời gian trung bình mỗi nước (giây)")
    axes[1].set_ylabel("seconds")
    axes[1].grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    out_path = out_dir / "evaluation_summary.png"
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_node_counts(summary_json, out_dir) -> Path:
    """So sánh avg_nodes_visited / avg_nodes_pruned giữa các model."""
    plt = _setup_matplotlib()
    with Path(summary_json).open(encoding="utf-8") as f:
        summary = json.load(f)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    names = list(summary.keys())
    visited = [summary[n].get("avg_nodes_visited_per_move", 0) for n in names]
    pruned = [summary[n].get("avg_nodes_pruned_per_move", 0) for n in names]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = list(range(len(names)))
    width = 0.35
    ax.bar([i - width / 2 for i in x], visited, width=width, label="visited", color="tab:blue")
    ax.bar([i + width / 2 for i in x], pruned, width=width, label="pruned", color="tab:orange")
    ax.set_xticks(x); ax.set_xticklabels(names)
    ax.set_title("Node thăm / Node cắt tỉa trung bình mỗi nước")
    ax.legend(); ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    out_path = out_dir / "node_counts.png"
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path
