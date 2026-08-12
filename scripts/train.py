"""Điểm vào huấn luyện self-play (Mô hình 3)."""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rl.q_learning import QLearning
from src.training.self_play import train
from src.board.state_resolver import resolve_state_key_fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--games", type=int, help="Ghi đè số ván self-play.")
    ap.add_argument("--max-moves", type=int, help="Ghi đè giới hạn half-move mỗi ván.")
    ap.add_argument("--save-every", type=int, help="Ghi đè chu kỳ lưu Q-table.")
    ap.add_argument("--q-table", help="Ghi đè đường dẫn lưu Q-table.")
    ap.add_argument("--history", help="Ghi đè đường dẫn CSV lịch sử train.")
    ap.add_argument("--resume", action="store_true", help="Load Q-table cũ trước khi train tiếp.")
    ap.add_argument("--seed", type=int, help="Seed để tái lập lựa chọn epsilon-greedy.")
    ap.add_argument("--no-replay", action="store_true", help="Tắt batch Q-update từ replay (chế độ legacy).")
    ap.add_argument("--no-progress", action="store_true", help="Tắt tqdm progress bar.")
    ap.add_argument("--state-representation", choices=["full", "compact"], help="Ghi đè state key cho Q-learning.")
    ap.add_argument("--q-value-step", type=float, help="Bật lượng tử Q-value theo bước này, ví dụ 0.05.")
    ap.add_argument("--q-value-clip", type=float, help="Clip Q-value vào [-clip, clip] trước khi lượng tử.")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))

    # Tách tham số non-QLearning ra khỏi q_kwargs
    q_cfg = dict(cfg["q_learning"])
    state_representation = q_cfg.pop("state_representation", "full")
    if args.state_representation:
        state_representation = args.state_representation
    batch_size = q_cfg.pop("batch_size", 0)
    batch_updates_per_game = q_cfg.pop("batch_updates_per_game", 0)
    warmup_games = q_cfg.pop("warmup_games", 0)
    if args.no_replay:
        batch_size = 0
        batch_updates_per_game = 0

    if args.seed is not None:
        q_cfg["seed"] = args.seed
    if args.q_value_step is not None:
        q_cfg["q_value_step"] = args.q_value_step
    if args.q_value_clip is not None:
        q_cfg["q_value_clip"] = args.q_value_clip
    q = QLearning(**q_cfg)
    t = cfg["training"]
    q_table_path = args.q_table or t["q_table_path"]
    if args.resume and Path(q_table_path).exists():
        q.load(q_table_path)
        print(f"[train] resumed Q-table from {q_table_path} with {len(q.q)} entries")

    train(
        q,
        args.games or t["num_games"],
        args.max_moves or t["max_moves"],
        args.save_every or t["save_every"],
        q_table_path,
        args.history or t.get("history_path"),
        batch_size=batch_size,
        batch_updates_per_game=batch_updates_per_game,
        warmup_games=warmup_games,
        state_key_fn=resolve_state_key_fn(state_representation),
        show_progress=not args.no_progress,
    )
    q.save(q_table_path)

    # Auto-plot training curves nếu config bật và matplotlib có sẵn
    if t.get("plot_after_training", False):
        try:
            from src.analytics.plots import plot_training_curves
            figures_dir = Path(cfg.get("evaluation", {}).get("figures_dir", "experiments/figures"))
            plot_training_curves(args.history or t.get("history_path"), figures_dir)
            print(f"[train] training curves saved to {figures_dir}")
        except Exception as e:
            print(f"[train] skip plotting: {e}")


if __name__ == "__main__":
    main()
