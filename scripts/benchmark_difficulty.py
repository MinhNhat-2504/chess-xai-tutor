"""Train and benchmark the 3 UI difficulty levels over multiple seeds.

Outputs:
- per_seed_games.csv: every game with side metrics
- per_seed_summary.csv: one row per seed and difficulty
- aggregate_summary.csv/json: mean/std over seeds
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from itertools import combinations
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.evaluate import OPENING_FENS, winner_name
from src.agents.difficulty import DIFFICULTY_CHOICES, DIFFICULTY_LABELS, build_difficulty_agent
from src.analytics.elo import compute_ratings
from src.board.chess_env import ChessEnv
from src.board.state_resolver import resolve_state_key_fn
from src.rl.q_learning import QLearning
from src.training.self_play import train


def parse_seeds(raw: str) -> list[int]:
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], 0.0
    return statistics.mean(values), statistics.stdev(values)


def train_seed_q_table(cfg: dict, args, seed: int, out_dir: Path) -> Path:
    q_cfg = dict(cfg["q_learning"])
    config_state_representation = q_cfg.pop("state_representation", "compact")
    state_representation = args.state_representation or config_state_representation
    for key in ("batch_size", "batch_updates_per_game", "warmup_games"):
        q_cfg.pop(key, None)
    q_cfg.update(
        {
            "seed": seed,
            "q_value_step": args.q_value_step,
            "q_value_clip": args.q_value_clip,
        }
    )
    q = QLearning(**q_cfg)
    q_table = out_dir / f"q_seed_{seed}.pkl"
    history = out_dir / f"training_seed_{seed}.csv"
    train(
        q,
        args.train_games,
        args.max_moves,
        max(1, args.train_games),
        q_table,
        history_path=history,
        batch_size=args.batch_size,
        batch_updates_per_game=args.batch_updates_per_game,
        warmup_games=args.warmup_games,
        state_key_fn=resolve_state_key_fn(state_representation),
        show_progress=not args.no_progress,
    )
    q.save(q_table)
    return q_table


def choose_timed(agent, env):
    start = time.perf_counter()
    move = agent.choose_move(env)
    elapsed = time.perf_counter() - start
    stats = getattr(agent, "last_stats", None)
    explanation = getattr(agent, "last_explanation", None) or {}
    return move, elapsed, stats, explanation


def play_game(white_name, white_agent, black_name, black_agent, max_moves, fen=None):
    env = ChessEnv(fen)
    metrics = {
        white_name: _empty_metrics(),
        black_name: _empty_metrics(),
    }

    for _ in range(max_moves):
        if env.is_terminal():
            break
        name, agent = (white_name, white_agent) if env.board.turn else (black_name, black_agent)
        move, elapsed, stats, explanation = choose_timed(agent, env)
        if move is None:
            break
        m = metrics[name]
        m["moves"] += 1
        m["time"] += elapsed
        if stats is not None:
            m["visited"] += stats.visited
            m["pruned"] += stats.pruned
            m["cache_hits"] += getattr(stats, "cache_hits", 0)
            m["q_visited"] += getattr(stats, "q_visited", 0)
            m["q_cutoffs"] += getattr(stats, "q_cutoffs", 0)
        m["mcts_visits"] += explanation.get("mcts_visits", 0)
        m["mcts_bonus_abs"] += abs(explanation.get("mcts_bonus", 0.0))
        m["q_bonus_abs"] += abs(explanation.get("q_bonus", 0.0))
        env.push(move)

    return env.result() if env.is_terminal() else "1/2-1/2", metrics, env.board.fullmove_number


def _empty_metrics():
    return {
        "moves": 0,
        "time": 0.0,
        "visited": 0,
        "pruned": 0,
        "cache_hits": 0,
        "q_visited": 0,
        "q_cutoffs": 0,
        "mcts_visits": 0,
        "mcts_bonus_abs": 0.0,
        "q_bonus_abs": 0.0,
    }


def update_summary(summary, row):
    for color in ("white", "black"):
        name = row[color]
        side = row[f"{color}_metrics"]
        entry = summary.setdefault(
            name,
            {
                "games": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                **_empty_metrics(),
            },
        )
        entry["games"] += 1
        for key in _empty_metrics():
            entry[key] += side[key]
        if row["winner"] == "draw":
            entry["draws"] += 1
        elif row["winner"] == name:
            entry["wins"] += 1
        else:
            entry["losses"] += 1


def finalize_summary(summary: dict, elo: dict[str, float]) -> dict:
    for name, entry in summary.items():
        moves = max(1, entry["moves"])
        games = max(1, entry["games"])
        entry["score_rate"] = (entry["wins"] + 0.5 * entry["draws"]) / games
        entry["elo"] = elo.get(name, 1500.0)
        entry["avg_time_per_move"] = entry["time"] / moves
        entry["avg_nodes_visited_per_move"] = entry["visited"] / moves
        entry["avg_nodes_pruned_per_move"] = entry["pruned"] / moves
        entry["avg_cache_hits_per_move"] = entry["cache_hits"] / moves
        entry["avg_q_nodes_per_move"] = entry["q_visited"] / moves
        entry["avg_mcts_visits_per_move"] = entry["mcts_visits"] / moves
        entry["avg_abs_mcts_bonus_per_move"] = entry["mcts_bonus_abs"] / moves
        entry["avg_abs_q_bonus_per_move"] = entry["q_bonus_abs"] / moves
    return summary


def benchmark_seed(cfg: dict, args, seed: int, q_table: Path):
    search_cfg = dict(cfg.get("search", {}))
    search_cfg.update(cfg.get("hybrid", {}) or {})
    search_cfg.update(
        {
            "medium_depth": args.medium_depth,
            "hell_depth": args.hell_depth,
            "hell_min_depth": args.hell_min_depth,
            "hell_use_iterative_deepening": args.hell_use_iterative_deepening,
            "hell_time_limit_s": args.hell_time_limit_s,
            "hell_mcts_iterations": args.hell_mcts_iterations,
            "hell_mcts_rollout_depth": args.hell_mcts_rollout_depth,
            "hell_mcts_weight": args.hell_mcts_weight,
        }
    )
    openings = [("start", None)] if args.openings == "start" else list(OPENING_FENS.items())
    rows = []
    summary = {}
    game_id = 1

    pairings = list(combinations(DIFFICULTY_CHOICES, 2))
    total = len(openings) * len(pairings) * args.eval_games
    done = 0

    for opening_name, opening_fen in openings:
        for left, right in pairings:
            for index in range(args.eval_games):
                agents = {
                    name: build_difficulty_agent(
                        name,
                        q_table=q_table,
                        search_cfg=search_cfg,
                        state_representation=args.state_representation,
                        seed=seed + game_id * 100 + offset,
                    )
                    for offset, name in enumerate(DIFFICULTY_CHOICES)
                }
                white, black = (left, right) if index % 2 == 0 else (right, left)
                result, metrics, fullmove_number = play_game(
                    white,
                    agents[white],
                    black,
                    agents[black],
                    args.max_moves,
                    opening_fen,
                )
                row = {
                    "seed": seed,
                    "game": game_id,
                    "opening": opening_name,
                    "white": white,
                    "black": black,
                    "result": result,
                    "winner": winner_name(result, white, black),
                    "fullmove_number": fullmove_number,
                    "white_metrics": metrics[white],
                    "black_metrics": metrics[black],
                }
                rows.append(row)
                update_summary(summary, row)
                done += 1
                if not args.no_progress:
                    print(
                        f"[bench seed={seed}] {done}/{total} {opening_name}: "
                        f"{white} vs {black} -> {result}"
                    )
                game_id += 1

    elo = compute_ratings(rows, k=cfg.get("evaluation", {}).get("elo_k_factor", 32))
    return rows, finalize_summary(summary, elo)


def flatten_game_row(row: dict) -> dict:
    out = {k: row[k] for k in ("seed", "game", "opening", "white", "black", "result", "winner", "fullmove_number")}
    for color in ("white", "black"):
        for key, value in row[f"{color}_metrics"].items():
            out[f"{color}_{key}"] = value
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(per_seed_rows: list[dict]) -> list[dict]:
    metrics = [
        "elo",
        "score_rate",
        "avg_time_per_move",
        "avg_nodes_visited_per_move",
        "avg_nodes_pruned_per_move",
        "avg_cache_hits_per_move",
        "avg_q_nodes_per_move",
        "avg_mcts_visits_per_move",
        "avg_abs_mcts_bonus_per_move",
        "avg_abs_q_bonus_per_move",
        "wins",
        "losses",
        "draws",
    ]
    output = []
    for difficulty in DIFFICULTY_CHOICES:
        group = [row for row in per_seed_rows if row["difficulty"] == difficulty]
        item = {"difficulty": difficulty, "label": DIFFICULTY_LABELS[difficulty], "seeds": len(group)}
        for metric in metrics:
            values = [float(row[metric]) for row in group]
            avg, std = mean_std(values)
            item[f"{metric}_mean"] = avg
            item[f"{metric}_std"] = std
        output.append(item)
    return output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--seeds", default="7,11,13,17,19")
    ap.add_argument("--out-dir", default="experiments/results/difficulty_benchmark")
    ap.add_argument("--train-games", type=int, default=120)
    ap.add_argument("--eval-games", type=int, default=2, help="Games per difficulty pair per seed/opening.")
    ap.add_argument("--max-moves", type=int, default=60)
    ap.add_argument("--openings", choices=["start", "suite"], default="start")
    ap.add_argument("--state-representation", choices=["full", "compact"], default="compact")
    ap.add_argument("--q-value-step", type=float, default=0.05)
    ap.add_argument("--q-value-clip", type=float, default=5.0)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--batch-updates-per-game", type=int, default=4)
    ap.add_argument("--warmup-games", type=int, default=20)
    ap.add_argument("--medium-depth", type=int, default=2)
    ap.add_argument("--hell-depth", type=int, default=2)
    ap.add_argument("--hell-min-depth", type=int, default=1)
    ap.add_argument("--hell-use-iterative-deepening", action="store_true")
    ap.add_argument("--hell-time-limit-s", type=float, default=0.25)
    ap.add_argument("--hell-mcts-iterations", type=int, default=80)
    ap.add_argument("--hell-mcts-rollout-depth", type=int, default=10)
    ap.add_argument("--hell-mcts-weight", type=float, default=120.0)
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--no-progress", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    seeds = parse_seeds(args.seeds)
    out_dir = Path(args.out_dir)
    all_game_rows = []
    per_seed_rows = []

    for seed in seeds:
        seed_dir = out_dir / f"seed_{seed}"
        q_table = seed_dir / f"q_seed_{seed}.pkl"
        if not args.skip_train or not q_table.exists():
            q_table = train_seed_q_table(cfg, args, seed, seed_dir)
        rows, summary = benchmark_seed(cfg, args, seed, q_table)
        all_game_rows.extend(flatten_game_row(row) for row in rows)
        for difficulty, entry in summary.items():
            per_seed_rows.append({"seed": seed, "difficulty": difficulty, "label": DIFFICULTY_LABELS[difficulty], **entry})

    aggregate_rows = aggregate(per_seed_rows)
    write_csv(out_dir / "per_seed_games.csv", all_game_rows)
    write_csv(out_dir / "per_seed_summary.csv", per_seed_rows)
    write_csv(out_dir / "aggregate_summary.csv", aggregate_rows)
    with (out_dir / "aggregate_summary.json").open("w", encoding="utf-8") as f:
        json.dump(aggregate_rows, f, ensure_ascii=False, indent=2)
    with (out_dir / "run_config.json").open("w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)

    print(f"[benchmark] saved {out_dir / 'aggregate_summary.csv'}")
    print(f"[benchmark] saved {out_dir / 'per_seed_summary.csv'}")
    print(f"[benchmark] saved {out_dir / 'per_seed_games.csv'}")
    print()
    for row in aggregate_rows:
        print(
            f"{row['difficulty']:>6s}: "
            f"ELO {row['elo_mean']:.1f}±{row['elo_std']:.1f} | "
            f"score {row['score_rate_mean']:.3f}±{row['score_rate_std']:.3f} | "
            f"time/move {row['avg_time_per_move_mean']:.4f}±{row['avg_time_per_move_std']:.4f}s | "
            f"nodes/move {row['avg_nodes_visited_per_move_mean']:.1f}±{row['avg_nodes_visited_per_move_std']:.1f} | "
            f"MCTS visits/move {row['avg_mcts_visits_per_move_mean']:.1f}±{row['avg_mcts_visits_per_move_std']:.1f}"
        )


if __name__ == "__main__":
    main()
