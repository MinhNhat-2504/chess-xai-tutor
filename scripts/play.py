"""Chơi cờ với một agent qua giao diện."""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui.app import run as run_console
from src.agents.minimax_agent import MinimaxAgent
from src.agents.alphabeta_agent import AlphaBetaAgent
from src.agents.hybrid_agent import HybridAgent
from src.agents.difficulty import DIFFICULTY_CHOICES, DIFFICULTY_LABELS, build_difficulty_agent
from src.board.state_resolver import resolve_state_key_fn
from src.rl.q_learning import QLearning


def build_agent(name, depth, q_table, search_cfg=None, state_representation="full"):
    sc = search_cfg or {}
    common = dict(
        use_transposition=sc.get("use_transposition", True),
        use_quiescence=sc.get("use_quiescence", False),
        q_max_depth=sc.get("q_max_depth", 6),
        use_iterative_deepening=sc.get("use_iterative_deepening", False),
        time_limit_s=sc.get("time_limit_s"),
        use_killer_moves=sc.get("use_killer_moves", False),
        use_history_heuristic=sc.get("use_history_heuristic", False),
    )
    if name == "minimax":
        return MinimaxAgent(depth=depth)
    if name == "alphabeta":
        return AlphaBetaAgent(depth=depth, **common)
    q = QLearning()
    q_path = Path(q_table)
    if q_path.exists():
        q.load(q_path)
    else:
        print(f"[play] Chưa có {q_path}; Hybrid dùng Q-table rỗng.")
    return HybridAgent(
        q,
        depth=depth,
        lam=sc.get("lambda", 0.5),
        state_key_fn=resolve_state_key_fn(state_representation),
        use_confidence=sc.get("use_confidence", False),
        confidence_k=sc.get("confidence_k", 10.0),
        **common,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=["minimax", "alphabeta", "hybrid"], default="hybrid")
    ap.add_argument("--difficulty", choices=DIFFICULTY_CHOICES, help="Preset demo: easy, medium, hell.")
    ap.add_argument("--depth", type=int, default=3, help="Độ sâu tìm kiếm của agent.")
    ap.add_argument("--q-table", default="data/q_tables/q_table.pkl", help="Đường dẫn Q-table cho hybrid.")
    ap.add_argument("--human-color", choices=["white", "black"], default="white", help="Màu quân người chơi.")
    ap.add_argument("--ui", choices=["console", "pygame"], default="console", help="Giao diện chơi.")
    ap.add_argument("--config", default="config/config.yaml", help="Config để đọc search flags.")
    ap.add_argument("--state-representation", choices=["full", "compact"], help="State key của Q-table hybrid.")
    args = ap.parse_args()

    search_cfg = {}
    ui_cfg = {}
    xai_cfg = {}
    state_representation = args.state_representation or "full"
    cfg_path = Path(args.config)
    if cfg_path.exists():
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
            search_cfg = cfg.get("search", {}) or {}
            search_cfg.update(cfg.get("hybrid", {}) or {})
            ui_cfg = cfg.get("ui", {}) or {}
            xai_cfg = cfg.get("xai", {}) or {}
            state_representation = args.state_representation or cfg.get("q_learning", {}).get("state_representation", "full")
        except Exception as e:
            print(f"[play] đọc config thất bại: {e}")

    import chess
    human_color = chess.WHITE if args.human_color == "white" else chess.BLACK
    pygame_cfg = ui_cfg.get("pygame", {}) if isinstance(ui_cfg.get("pygame", {}), dict) else {}
    square_size = int(pygame_cfg.get("square_size", 64))
    difficulty = args.difficulty
    if args.ui == "pygame" and difficulty is None:
        from src.ui.pygame_app import select_difficulty_menu
        default_difficulty = ui_cfg.get("difficulty", "medium")
        if default_difficulty not in DIFFICULTY_CHOICES:
            default_difficulty = "medium"
        difficulty = select_difficulty_menu(
            DIFFICULTY_LABELS,
            default=default_difficulty,
            square_size=square_size,
        )
        if difficulty is None:
            print("[play] Đã thoát trước khi bắt đầu ván.")
            return

    difficulty_label = None
    if difficulty:
        if difficulty == "hell" and not Path(args.q_table).exists():
            print(f"[play] Chưa có {args.q_table}; Hell dùng Q-table rỗng nhưng vẫn bật quantized Q + MCTS.")
        agent = build_difficulty_agent(
            difficulty,
            q_table=args.q_table,
            search_cfg=search_cfg,
            state_representation="compact" if difficulty == "hell" else state_representation,
        )
        difficulty_label = DIFFICULTY_LABELS[difficulty]
        print(f"[play] Difficulty: {difficulty_label}")
    else:
        agent = build_agent(
            args.agent,
            args.depth,
            args.q_table,
            search_cfg=search_cfg,
            state_representation=state_representation,
        )

    if args.ui == "pygame":
        from src.ui.pygame_app import run_gui
        explainer = None
        if xai_cfg.get("live_explanations", True):
            from src.xai import MoveExplainer
            explainer = MoveExplainer(
                depth=2,
                use_stockfish=xai_cfg.get("use_stockfish", True),
                engine_path=xai_cfg.get("engine_path"),
                engine_depth=int(xai_cfg.get("engine_depth", 12)),
                multipv=int(xai_cfg.get("multipv", 3)),
                engine_time_s=xai_cfg.get("engine_time_s", 1.0),
            )
            print(f"[play] Giải thích nước đi: {explainer.engine_label}")
        try:
            run_gui(
                agent,
                human_color=human_color,
                square_size=square_size,
                difficulty_label=difficulty_label,
                explainer=explainer,
            )
        finally:
            if explainer is not None:
                explainer.close()
    else:
        run_console(agent, human_color=human_color)


if __name__ == "__main__":
    main()
