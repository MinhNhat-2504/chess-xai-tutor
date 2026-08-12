"""Difficulty presets for human-facing play."""
from __future__ import annotations

import random
from pathlib import Path

from ..board.state_resolver import resolve_state_key_fn
from ..evaluation.evaluator import evaluate
from ..rl.q_learning import QLearning
from .alphabeta_agent import AlphaBetaAgent
from .base_agent import BaseAgent
from .hybrid_agent import HybridAgent


DIFFICULTY_CHOICES = ("easy", "medium", "hell")

DIFFICULTY_LABELS = {
    "easy": "Dễ",
    "medium": "Trung bình",
    "hell": "Siêu khó địa ngục",
}


class EasyBlunderAgent(BaseAgent):
    """A deliberately weak agent for new players."""

    def __init__(self, blunder_rate: float = 0.85, seed: int | None = None):
        self.blunder_rate = blunder_rate
        self.rng = random.Random(seed)
        self.depth = 1
        self.last_stats = None
        self.last_info = None
        self.last_explanation = None

    def choose_move(self, env):
        moves = env.legal_moves()
        if not moves:
            return None
        perspective = env.board.turn
        scored = []
        for move in moves:
            env.push(move)
            score = evaluate(env.board, perspective)
            env.pop()
            scored.append((score, move))

        scored.sort(key=lambda item: item[0])
        if self.rng.random() < self.blunder_rate:
            pool_size = max(1, len(scored) // 3)
            pool = scored[:pool_size]
        else:
            pool_size = max(1, len(scored) // 2)
            pool = scored[:pool_size]
        score, move = self.rng.choice(pool)
        self.last_explanation = {
            "move": move.uci(),
            "alphabeta_score": score,
            "q_value": 0.0,
            "confidence": 0.0,
            "q_bonus": 0.0,
            "mcts_score": 0.0,
            "mcts_visits": 0,
            "mcts_bonus": 0.0,
            "memory_hit": False,
            "final_score": score,
        }
        return move


def build_difficulty_agent(
    difficulty: str,
    q_table: str | Path = "data/q_tables/q_quantized.pkl",
    search_cfg: dict | None = None,
    state_representation: str = "compact",
    seed: int | None = None,
):
    """Create a demo agent matching the requested difficulty label."""
    if difficulty not in DIFFICULTY_CHOICES:
        raise ValueError(f"Unknown difficulty: {difficulty}")

    sc = search_cfg or {}
    if difficulty == "easy":
        return EasyBlunderAgent(seed=seed)

    if difficulty == "medium":
        return AlphaBetaAgent(
            depth=max(2, int(sc.get("medium_depth", 3))),
            use_transposition=True,
            use_quiescence=True,
            q_max_depth=4,
            use_iterative_deepening=False,
            use_killer_moves=True,
            use_history_heuristic=True,
        )

    q = QLearning(
        epsilon=0.0,
        q_value_step=sc.get("hell_q_value_step", 0.05),
        q_value_clip=sc.get("hell_q_value_clip", 5.0),
        seed=seed,
    )
    q_path = Path(q_table)
    if q_path.exists():
        q.load(q_path)

    hell_depth = max(int(sc.get("hell_min_depth", 4)), int(sc.get("hell_depth", 4)))
    return HybridAgent(
        q,
        depth=hell_depth,
        lam=float(sc.get("lambda", 0.5)),
        use_transposition=True,
        use_quiescence=True,
        q_max_depth=int(sc.get("hell_q_max_depth", 6)),
        use_iterative_deepening=sc.get("hell_use_iterative_deepening", True),
        time_limit_s=sc.get("hell_time_limit_s", 1.0),
        use_killer_moves=True,
        use_history_heuristic=True,
        state_key_fn=resolve_state_key_fn(state_representation),
        use_confidence=True,
        confidence_k=float(sc.get("confidence_k", 10.0)),
        use_mcts=True,
        mcts_iterations=int(sc.get("hell_mcts_iterations", 180)),
        mcts_rollout_depth=int(sc.get("hell_mcts_rollout_depth", 14)),
        mcts_weight=float(sc.get("hell_mcts_weight", 120.0)),
        mcts_seed=seed,
        mcts_time_limit_s=sc.get("hell_mcts_time_limit_s", 0.45),
        enable_memory=sc.get("hell_use_memory", True),
        memory_path=sc.get("hell_memory_path", "data/move_cache/hell_memory.json"),
    )

