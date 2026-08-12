"""So sánh 3 mô hình — Báo cáo mục 4.4, 4.5.

Cho các agent đối đầu, ghi: win/loss/draw, thời gian/nước đi, node duyệt, node cắt tỉa.
Kết quả lưu CSV/JSON vào experiments/results để vẽ biểu đồ (mục 4.6).

Bản nâng cấp:
- Xuất PGN của từng ván (mục 4.5) → mở trong lichess analysis.
- Tính ELO rating tuần tự (mục 4.4.4).
- tqdm progress bar (mục 4.4.5).
- Auto-render biểu đồ sau khi đánh giá.
"""
import argparse
import csv
import json
import sys
import time
from itertools import combinations
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.alphabeta_agent import AlphaBetaAgent
from src.agents.difficulty_agent import DifficultyAgent, DIFFICULTY_NAMES, build_difficulty_profile
from src.agents.hybrid_agent import HybridAgent
from src.agents.minimax_agent import MinimaxAgent
from src.board.chess_env import ChessEnv
from src.board.state_resolver import resolve_state_key_fn
from src.rl.q_learning import QLearning
from src.analytics.pgn_writer import game_to_pgn, append_pgn_file
from src.analytics.elo import compute_ratings


OPENING_FENS = {
    "start": None,
    "italian": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 3",
    "sicilian": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
    "french": "rnbqkbnr/ppp2ppp/4p3/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3",
    "queens_gambit": "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2",
    "kings_indian": "rnbqkb1r/pppppppp/5n2/8/3P4/5N2/PPP1PPPP/RNBQKB1R b KQkq - 2 2",
}


def _legacy_build_agents(cfg, depth, q_table_path=None, state_representation=None):
    # Tách các tham số non-QLearning ra
    q_cfg = dict(cfg["q_learning"])
    state_representation = state_representation or q_cfg.get("state_representation", "full")
    for k in ("state_representation", "batch_size", "batch_updates_per_game", "warmup_games"):
        q_cfg.pop(k, None)
    q = QLearning(**q_cfg)
    q_path = Path(q_table_path or cfg["training"]["q_table_path"])
    if q_path.exists():
        q.load(q_path)
    else:
        print(f"[evaluate] Chưa có {q_path}; Hybrid dùng Q-table rỗng.")

    s = cfg["search"]
    use_tt = s.get("use_transposition", True)
    use_q = s.get("use_quiescence", False)
    q_max = s.get("q_max_depth", 6)
    return {
        "minimax": MinimaxAgent(depth=depth),
        "alphabeta": AlphaBetaAgent(
            depth=depth, use_transposition=use_tt, use_quiescence=use_q, q_max_depth=q_max
        ),
        "hybrid": HybridAgent(
            q, depth=depth, lam=cfg["hybrid"]["lambda"],
            use_transposition=use_tt, use_quiescence=use_q, q_max_depth=q_max,
            state_key_fn=resolve_state_key_fn(state_representation),
            use_confidence=cfg["hybrid"].get("use_confidence", False),
            confidence_k=cfg["hybrid"].get("confidence_k", 10.0),
        ),
    }


def build_single_agent(cfg, name, depth, q_table_path=None, state_representation=None,
                       difficulty=None, seed=None):
    profile = build_difficulty_profile(difficulty, cfg) if difficulty else None
    search_cfg = dict(cfg["search"])
    if profile:
        search_cfg.update(profile.search_overrides)
        depth = profile.depth if depth is None else depth
    depth = depth or cfg["search"]["max_depth"]

    q_cfg = dict(cfg["q_learning"])
    state_representation = state_representation or q_cfg.get("state_representation", "full")
    for k in ("state_representation", "batch_size", "batch_updates_per_game", "warmup_games"):
        q_cfg.pop(k, None)
    if seed is not None:
        q_cfg["seed"] = seed

    common = dict(
        use_transposition=search_cfg.get("use_transposition", True),
        use_quiescence=search_cfg.get("use_quiescence", False),
        q_max_depth=search_cfg.get("q_max_depth", 6),
        use_iterative_deepening=search_cfg.get("use_iterative_deepening", False),
        time_limit_s=search_cfg.get("time_limit_s"),
        use_killer_moves=search_cfg.get("use_killer_moves", False),
        use_history_heuristic=search_cfg.get("use_history_heuristic", False),
    )

    if name == "minimax":
        agent = MinimaxAgent(depth=depth)
    elif name == "alphabeta":
        agent = AlphaBetaAgent(depth=depth, **common)
    else:
        q = QLearning(**q_cfg)
        q_path = Path(q_table_path or cfg["training"]["q_table_path"])
        if q_path.exists():
            q.load(q_path)
        else:
            print(f"[evaluate] Chua co {q_path}; Hybrid dung Q-table rong.")
        agent = HybridAgent(
            q,
            depth=depth,
            lam=cfg["hybrid"]["lambda"],
            state_key_fn=resolve_state_key_fn(state_representation),
            use_confidence=cfg["hybrid"].get("use_confidence", False),
            confidence_k=cfg["hybrid"].get("confidence_k", 10.0),
            **common,
        )

    return DifficultyAgent(agent, profile, seed=seed) if profile else agent


def build_agents(cfg, depth, q_table_path=None, state_representation=None,
                 difficulty=None, difficulty_suite=False, base_agent_name="hybrid", seed=None):
    if difficulty_suite:
        return {
            profile_name: build_single_agent(
                cfg,
                base_agent_name,
                depth,
                q_table_path,
                state_representation,
                difficulty=profile_name,
                seed=seed,
            )
            for profile_name in DIFFICULTY_NAMES
        }

    if difficulty:
        return {
            "minimax": build_single_agent(cfg, "minimax", depth, q_table_path, state_representation, difficulty=difficulty, seed=seed),
            "alphabeta": build_single_agent(cfg, "alphabeta", depth, q_table_path, state_representation, difficulty=difficulty, seed=seed),
            "hybrid": build_single_agent(cfg, "hybrid", depth, q_table_path, state_representation, difficulty=difficulty, seed=seed),
        }
    return {
        "minimax": build_single_agent(cfg, "minimax", depth, q_table_path, state_representation, seed=seed),
        "alphabeta": build_single_agent(cfg, "alphabeta", depth, q_table_path, state_representation, seed=seed),
        "hybrid": build_single_agent(cfg, "hybrid", depth, q_table_path, state_representation, seed=seed),
    }


def choose_timed(agent, env):
    start = time.perf_counter()
    move = agent.choose_move(env)
    elapsed = time.perf_counter() - start
    stats = getattr(agent, "last_stats", None)
    return move, elapsed, stats


def play_game(white_name, white_agent, black_name, black_agent, max_moves, fen=None):
    env = ChessEnv(fen)
    metrics = {
        white_name: {"moves": 0, "time": 0.0, "visited": 0, "pruned": 0, "cache_hits": 0},
        black_name: {"moves": 0, "time": 0.0, "visited": 0, "pruned": 0, "cache_hits": 0},
    }
    moves_played = []

    for _ in range(max_moves):
        if env.is_terminal():
            break
        name, agent = (white_name, white_agent) if env.board.turn else (black_name, black_agent)
        move, elapsed, stats = choose_timed(agent, env)
        if move is None:
            break
        metrics[name]["moves"] += 1
        metrics[name]["time"] += elapsed
        if stats is not None:
            metrics[name]["visited"] += stats.visited
            metrics[name]["pruned"] += stats.pruned
            metrics[name]["cache_hits"] += getattr(stats, "cache_hits", 0)
        env.push(move)
        moves_played.append(move)

    result = env.result() if env.is_terminal() else "1/2-1/2"
    return result, metrics, env.board.fullmove_number, moves_played


def winner_name(result, white_name, black_name):
    if result == "1-0":
        return white_name
    if result == "0-1":
        return black_name
    return "draw"


def update_summary(summary, row):
    for color in ("white", "black"):
        name = row[color]
        side_metrics = row[f"{color}_metrics"]
        entry = summary.setdefault(
            name,
            {
                "games": 0, "wins": 0, "losses": 0, "draws": 0,
                "moves": 0, "time": 0.0,
                "visited": 0, "pruned": 0, "cache_hits": 0,
            },
        )
        entry["games"] += 1
        entry["moves"] += side_metrics["moves"]
        entry["time"] += side_metrics["time"]
        entry["visited"] += side_metrics["visited"]
        entry["pruned"] += side_metrics["pruned"]
        entry["cache_hits"] += side_metrics["cache_hits"]
        if row["winner"] == "draw":
            entry["draws"] += 1
        elif row["winner"] == name:
            entry["wins"] += 1
        else:
            entry["losses"] += 1


def normalize_summary(summary):
    for entry in summary.values():
        moves = max(entry["moves"], 1)
        entry["avg_time_per_move"] = entry["time"] / moves
        entry["avg_nodes_visited_per_move"] = entry["visited"] / moves
        entry["avg_nodes_pruned_per_move"] = entry["pruned"] / moves
        entry["avg_cache_hits_per_move"] = entry["cache_hits"] / moves
    return summary


def write_outputs(rows, summary, results_dir, elo: dict | None = None):
    results_dir.mkdir(parents=True, exist_ok=True)
    games_path = results_dir / "games.csv"
    with games_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "game", "opening", "white", "black", "result", "winner", "fullmove_number",
                "white_moves", "white_time", "white_nodes_visited", "white_nodes_pruned",
                "white_cache_hits",
                "black_moves", "black_time", "black_nodes_visited", "black_nodes_pruned",
                "black_cache_hits",
            ],
        )
        writer.writeheader()
        for row in rows:
            white = row["white_metrics"]
            black = row["black_metrics"]
            writer.writerow({
                "game": row["game"],
                "opening": row.get("opening", "start"),
                "white": row["white"],
                "black": row["black"],
                "result": row["result"],
                "winner": row["winner"],
                "fullmove_number": row["fullmove_number"],
                "white_moves": white["moves"],
                "white_time": white["time"],
                "white_nodes_visited": white["visited"],
                "white_nodes_pruned": white["pruned"],
                "white_cache_hits": white["cache_hits"],
                "black_moves": black["moves"],
                "black_time": black["time"],
                "black_nodes_visited": black["visited"],
                "black_nodes_pruned": black["pruned"],
                "black_cache_hits": black["cache_hits"],
            })

    summary_path = results_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    elo_path = None
    if elo is not None:
        elo_path = results_dir / "elo.json"
        with elo_path.open("w", encoding="utf-8") as f:
            json.dump(elo, f, ensure_ascii=False, indent=2)

    return games_path, summary_path, elo_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/config.yaml")
    ap.add_argument("--games", type=int, help="Số ván cho mỗi cặp model.")
    ap.add_argument("--depth", type=int, help="Độ sâu tìm kiếm khi đánh giá.")
    ap.add_argument("--max-moves", type=int, help="Giới hạn half-move mỗi ván.")
    ap.add_argument("--no-pgn", action="store_true", help="Bỏ qua xuất PGN.")
    ap.add_argument("--no-elo", action="store_true", help="Bỏ qua tính ELO.")
    ap.add_argument("--no-progress", action="store_true", help="Tắt tqdm progress bar.")
    ap.add_argument("--no-plot", action="store_true", help="Không auto-render biểu đồ.")
    ap.add_argument("--q-table", help="Ghi đè Q-table cho Hybrid.")
    ap.add_argument("--state-representation", choices=["full", "compact"], help="Ghi đè state key cho Hybrid.")
    ap.add_argument("--openings", choices=["start", "suite"], default="start", help="Benchmark từ vị trí đầu hoặc bộ khai cuộc.")
    ap.add_argument("--difficulty", choices=["none", *DIFFICULTY_NAMES], help="Apply one difficulty profile to all evaluated agents.")
    ap.add_argument("--difficulty-suite", action="store_true", help="Evaluate easy/medium/hard as separate agents.")
    ap.add_argument("--difficulty-base-agent", choices=["minimax", "alphabeta", "hybrid"], default="hybrid", help="Base engine used by --difficulty-suite.")
    ap.add_argument("--seed", type=int, help="Seed for Q-learning and stochastic difficulty choices.")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    depth = args.depth
    if depth is None and not args.difficulty_suite and args.difficulty in (None, "none"):
        depth = cfg["search"]["max_depth"]
    games_per_pair = args.games or cfg["evaluation"]["games_per_pair"]
    max_moves = args.max_moves or cfg["training"]["max_moves"]
    results_dir = Path(cfg["evaluation"]["results_dir"])
    figures_dir = Path(cfg["evaluation"].get("figures_dir", "experiments/figures"))

    eval_cfg = cfg["evaluation"]
    export_pgn = eval_cfg.get("export_pgn", True) and not args.no_pgn
    compute_elo = eval_cfg.get("compute_elo", True) and not args.no_elo
    show_progress = eval_cfg.get("show_progress", True) and not args.no_progress
    elo_k = eval_cfg.get("elo_k_factor", 32)
    pgn_path = results_dir / "games.pgn"
    if export_pgn:
        pgn_path.parent.mkdir(parents=True, exist_ok=True)
        if pgn_path.exists():
            pgn_path.unlink()  # ghi đè ván cũ

    # Tính tổng số game để progress bar biết tổng
    difficulty = None if args.difficulty == "none" else args.difficulty
    agent_names = list(build_agents(
        cfg,
        depth,
        args.q_table,
        args.state_representation,
        difficulty=difficulty,
        difficulty_suite=args.difficulty_suite,
        base_agent_name=args.difficulty_base_agent,
        seed=args.seed,
    ).keys())
    pairings = list(combinations(agent_names, 2))
    openings = [("start", None)] if args.openings == "start" else list(OPENING_FENS.items())
    total_games = len(pairings) * games_per_pair * len(openings)

    pbar = None
    if show_progress:
        try:
            from tqdm import tqdm
            pbar = tqdm(total=total_games, desc="evaluate", unit="game")
        except ImportError:
            pbar = None

    rows = []
    summary = {}
    game_id = 1
    for opening_name, opening_fen in openings:
        for left, right in pairings:
            for index in range(games_per_pair):
                agents = build_agents(
                    cfg,
                    depth,
                    args.q_table,
                    args.state_representation,
                    difficulty=difficulty,
                    difficulty_suite=args.difficulty_suite,
                    base_agent_name=args.difficulty_base_agent,
                    seed=args.seed,
                )
                white_name, black_name = (left, right) if index % 2 == 0 else (right, left)
                result, metrics, fullmove_number, moves_played = play_game(
                    white_name, agents[white_name], black_name, agents[black_name], max_moves, opening_fen
                )
                row = {
                    "game": game_id,
                    "opening": opening_name,
                    "white": white_name,
                    "black": black_name,
                    "result": result,
                    "winner": winner_name(result, white_name, black_name),
                    "fullmove_number": fullmove_number,
                    "white_metrics": metrics[white_name],
                    "black_metrics": metrics[black_name],
                }
                rows.append(row)
                update_summary(summary, row)

                if export_pgn:
                    pgn = game_to_pgn(
                        moves_played, white_name, black_name, result,
                        headers_extra={"Round": str(game_id), "Depth": str(depth), "Opening": opening_name},
                        starting_fen=opening_fen,
                    )
                    append_pgn_file(pgn_path, pgn)

                if pbar is not None:
                    pbar.set_postfix_str(f"{opening_name}: {white_name} vs {black_name} → {result}")
                    pbar.update(1)
                else:
                    print(
                        f"[evaluate] game {game_id}: {opening_name} | {white_name} vs {black_name} "
                        f"=> {result} ({row['winner']})"
                    )
                game_id += 1

    if pbar is not None:
        pbar.close()

    elo = compute_ratings(rows, k=elo_k) if compute_elo else None
    games_path, summary_path, elo_path = write_outputs(
        rows, normalize_summary(summary), results_dir, elo=elo,
    )
    print(f"[evaluate] saved {games_path}")
    print(f"[evaluate] saved {summary_path}")
    if export_pgn:
        print(f"[evaluate] saved {pgn_path}")
    if elo_path:
        print(f"[evaluate] saved {elo_path}")
        for name, r in sorted(elo.items(), key=lambda kv: -kv[1]):
            print(f"            ELO {name:>10s}: {r:.0f}")

    if not args.no_plot:
        try:
            from src.analytics.plots import plot_evaluation_summary, plot_node_counts
            plot_evaluation_summary(summary_path, figures_dir)
            plot_node_counts(summary_path, figures_dir)
            print(f"[evaluate] figures saved to {figures_dir}")
        except Exception as e:
            print(f"[evaluate] skip plotting: {e}")


if __name__ == "__main__":
    main()
