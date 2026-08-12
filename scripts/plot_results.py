"""CLI vẽ lại biểu đồ phân tích từ CSV/JSON sẵn có — không cần chạy lại ván."""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.plots import (
    plot_training_curves,
    plot_evaluation_summary,
    plot_node_counts,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--history", help="Ghi đè đường dẫn training_history.csv")
    ap.add_argument("--summary", help="Ghi đè đường dẫn summary.json")
    ap.add_argument("--out", help="Ghi đè thư mục xuất figure")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    history_path = Path(args.history or cfg["training"].get("history_path", "experiments/results/training_history.csv"))
    summary_path = Path(args.summary or Path(cfg["evaluation"]["results_dir"]) / "summary.json")
    out_dir = Path(args.out or cfg["evaluation"]["figures_dir"])

    if history_path.exists():
        out = plot_training_curves(history_path, out_dir)
        print(f"[plot] saved training curves → {out}")
    else:
        print(f"[plot] skip training (không có {history_path})")

    if summary_path.exists():
        out = plot_evaluation_summary(summary_path, out_dir)
        print(f"[plot] saved evaluation summary → {out}")
        out = plot_node_counts(summary_path, out_dir)
        print(f"[plot] saved node counts → {out}")
    else:
        print(f"[plot] skip evaluation (không có {summary_path})")


if __name__ == "__main__":
    main()
