"""Hybrid agent: Alpha-Beta search plus Q-learning and optional MCTS/root memory."""
from __future__ import annotations

import json
import math
from pathlib import Path

import chess

from .base_agent import BaseAgent
from ..board.state import state_key
from ..evaluation.evaluator import evaluate
from ..search.alphabeta import SearchStats, alphabeta
from ..search.heuristics import HistoryTable, KillerTable
from ..search.iterative_deepening import search_iterative_root
from ..search.mcts import mcts_scores
from ..search.move_ordering import order_moves
from ..search.transposition import TranspositionTable


class HybridAgent(BaseAgent):
    def __init__(
        self,
        q_table,
        depth=4,
        lam=0.5,
        use_transposition=True,
        use_quiescence=False,
        q_max_depth=6,
        use_iterative_deepening=False,
        time_limit_s=None,
        use_killer_moves=False,
        use_history_heuristic=False,
        state_key_fn=state_key,
        use_confidence=False,
        confidence_k=10.0,
        use_mcts=False,
        mcts_iterations=300,
        mcts_rollout_depth=18,
        mcts_weight=0.0,
        mcts_seed=None,
        mcts_time_limit_s=None,
        memory_path=None,
        enable_memory=False,
    ):
        self.q = q_table
        self.depth = max(1, depth)
        self.lam = lam
        self.use_transposition = use_transposition
        self.use_quiescence = use_quiescence
        self.q_max_depth = q_max_depth
        self.use_iterative_deepening = use_iterative_deepening
        self.time_limit_s = time_limit_s
        self.use_killer_moves = use_killer_moves
        self.use_history_heuristic = use_history_heuristic
        self.state_key_fn = state_key_fn
        self.use_confidence = use_confidence
        self.confidence_k = confidence_k
        self.use_mcts = use_mcts
        self.mcts_iterations = mcts_iterations
        self.mcts_rollout_depth = mcts_rollout_depth
        self.mcts_weight = mcts_weight
        self.mcts_seed = mcts_seed
        self.mcts_time_limit_s = mcts_time_limit_s
        self._mcts_calls = 0
        self.enable_memory = enable_memory
        self.memory_path = Path(memory_path) if memory_path else None
        self._move_memory = self._load_memory()
        self.last_stats = None
        self.last_info = None
        self.last_explanation = None
        self.last_candidates = []
        self.last_mcts_scores = {}
        self.last_memory_hit = False

    def choose_move(self, env):
        memory_key = self._memory_key(env.board)
        cached_move = self._lookup_memory(env.board, memory_key)
        if cached_move is not None:
            return cached_move

        if self.use_iterative_deepening:
            move = self._choose_iterative(env)
        else:
            move = self._choose_fixed(env)
        self._remember_move(memory_key, move)
        return move

    def _choose_fixed(self, env):
        perspective = env.board.turn
        stats = SearchStats()
        transposition = TranspositionTable() if self.use_transposition else None
        killer_tbl = KillerTable() if self.use_killer_moves else None
        history_tbl = HistoryTable() if self.use_history_heuristic else None
        s = self.state_key_fn(env.board)
        root_mcts = self._root_mcts_scores(env.board, perspective)
        best_move, best_score = None, -math.inf
        candidates = []
        for move in order_moves(env.board, env.legal_moves()):
            env.push(move)
            mm = alphabeta(
                env,
                self.depth - 1,
                -math.inf,
                math.inf,
                False,
                evaluate,
                stats,
                perspective,
                transposition,
                killer_tbl=killer_tbl,
                history_tbl=history_tbl,
                use_quiescence=self.use_quiescence,
                q_max_depth=self.q_max_depth,
                ply=1,
            )
            env.pop()
            explanation = self._score_explanation(s, move, mm, root_mcts)
            candidates.append(explanation)
            if explanation["final_score"] > best_score:
                best_score, best_move = explanation["final_score"], move
                self.last_explanation = explanation
        self.last_stats = stats
        self.last_info = None
        self.last_candidates = sorted(candidates, key=lambda item: item["final_score"], reverse=True)
        self.last_memory_hit = False
        return best_move

    def _choose_iterative(self, env):
        perspective = env.board.turn
        s = self.state_key_fn(env.board)
        root_mcts = self._root_mcts_scores(env.board, perspective)

        def root_bonus(move_uci: str) -> float:
            q_bonus = self.lam * self._confidence(s, move_uci) * self.q.get(s, move_uci)
            mcts_score = root_mcts.get(move_uci)
            mcts_bonus = self.mcts_weight * mcts_score.mean_value if mcts_score else 0.0
            return q_bonus + mcts_bonus

        best_move, _, stats, info = search_iterative_root(
            env,
            self.depth,
            evaluate,
            perspective,
            time_limit_s=self.time_limit_s,
            use_quiescence=self.use_quiescence,
            q_max_depth=self.q_max_depth,
            use_killer_moves=self.use_killer_moves,
            use_history_heuristic=self.use_history_heuristic,
            root_bonus_fn=root_bonus,
        )
        self.last_stats = stats
        self.last_info = info
        self.last_memory_hit = False
        if best_move is not None and info:
            self.last_candidates = self._augment_iterative_candidates(s, info[-1].get("candidates", []), root_mcts)
            self.last_explanation = next(
                (item for item in self.last_candidates if item["move"] == best_move.uci()),
                None,
            )
            if self.last_explanation is None:
                q_bonus = self.lam * self._confidence(s, best_move.uci()) * self.q.get(s, best_move.uci())
                mcts_score = root_mcts.get(best_move.uci())
                mcts_bonus = self.mcts_weight * mcts_score.mean_value if mcts_score else 0.0
                self.last_explanation = self._explanation(
                    best_move,
                    info[-1]["value"] - q_bonus - mcts_bonus,
                    self.q.get(s, best_move.uci()),
                    self._confidence(s, best_move.uci()),
                    q_bonus,
                    info[-1]["value"],
                    mcts_score=mcts_score.mean_value if mcts_score else 0.0,
                    mcts_visits=mcts_score.visits if mcts_score else 0,
                    mcts_bonus=mcts_bonus,
                )
        return best_move

    def _score_explanation(self, state, move, alphabeta_score, root_mcts):
        q = self.q.get(state, move.uci())
        confidence = self._confidence(state, move.uci())
        q_bonus = self.lam * confidence * q
        mcts_score = root_mcts.get(move.uci())
        mcts_bonus = self.mcts_weight * mcts_score.mean_value if mcts_score else 0.0
        final_score = alphabeta_score + q_bonus + mcts_bonus
        return self._explanation(
            move,
            alphabeta_score,
            q,
            confidence,
            q_bonus,
            final_score,
            mcts_score=mcts_score.mean_value if mcts_score else 0.0,
            mcts_visits=mcts_score.visits if mcts_score else 0,
            mcts_bonus=mcts_bonus,
        )

    def _confidence(self, state: str, move_uci: str) -> float:
        if not self.use_confidence:
            return 1.0
        if hasattr(self.q, "confidence"):
            return self.q.confidence(state, move_uci, self.confidence_k)
        return 0.0

    def _root_mcts_scores(self, board, perspective):
        if not self.use_mcts or self.mcts_weight == 0.0:
            self.last_mcts_scores = {}
            return {}
        scores = mcts_scores(
            board,
            perspective,
            iterations=self.mcts_iterations,
            rollout_depth=self.mcts_rollout_depth,
            seed=None if self.mcts_seed is None else self.mcts_seed + self._mcts_calls,
            time_limit_s=self.mcts_time_limit_s,
        )
        self._mcts_calls += 1
        self.last_mcts_scores = scores
        return scores

    def _memory_key(self, board) -> str:
        return state_key(board)

    def _load_memory(self) -> dict:
        if not self.enable_memory or self.memory_path is None or not self.memory_path.exists():
            return {}
        try:
            with self.memory_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _save_memory(self) -> None:
        if not self.enable_memory or self.memory_path is None:
            return
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with self.memory_path.open("w", encoding="utf-8") as f:
            json.dump(self._move_memory, f, ensure_ascii=False, indent=2)

    def _lookup_memory(self, board, key):
        self.last_memory_hit = False
        if not self.enable_memory:
            return None
        entry = self._move_memory.get(key)
        if not isinstance(entry, dict):
            return None
        try:
            move = chess.Move.from_uci(entry.get("move", ""))
        except ValueError:
            self._move_memory.pop(key, None)
            return None
        if move not in board.legal_moves:
            self._move_memory.pop(key, None)
            return None

        explanation = dict(entry.get("explanation") or {"move": move.uci(), "final_score": 0.0})
        explanation["memory_hit"] = True
        explanation["move"] = move.uci()
        self.last_stats = SearchStats()
        self.last_info = None
        self.last_candidates = list(entry.get("candidates") or [explanation])
        self.last_explanation = explanation
        self.last_mcts_scores = {}
        self.last_memory_hit = True
        return move

    def _remember_move(self, key, move) -> None:
        if not self.enable_memory or move is None:
            return
        entry = {
            "move": move.uci(),
            "explanation": self._json_safe_dict(self.last_explanation or {"move": move.uci()}),
            "candidates": [self._json_safe_dict(item) for item in self.last_candidates[:8]],
        }
        entry["explanation"]["memory_hit"] = False
        self._move_memory[key] = entry
        self._save_memory()

    @staticmethod
    def _json_safe_dict(item: dict) -> dict:
        out = {}
        for key, value in dict(item).items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                out[key] = value
        return out

    @staticmethod
    def _explanation(
        move,
        alphabeta_score,
        q_value,
        confidence,
        q_bonus,
        final_score,
        mcts_score=0.0,
        mcts_visits=0,
        mcts_bonus=0.0,
    ):
        return {
            "move": move.uci(),
            "alphabeta_score": alphabeta_score,
            "q_value": q_value,
            "confidence": confidence,
            "q_bonus": q_bonus,
            "mcts_score": mcts_score,
            "mcts_visits": mcts_visits,
            "mcts_bonus": mcts_bonus,
            "memory_hit": False,
            "final_score": final_score,
        }

    def _augment_iterative_candidates(self, state, candidates, root_mcts):
        out = []
        for item in candidates:
            move_uci = item["move"]
            q = self.q.get(state, move_uci)
            confidence = self._confidence(state, move_uci)
            q_bonus = self.lam * confidence * q
            mcts_score = root_mcts.get(move_uci)
            mcts_bonus = self.mcts_weight * mcts_score.mean_value if mcts_score else 0.0
            out.append({
                "move": move_uci,
                "alphabeta_score": item.get("alphabeta_score", item["final_score"] - q_bonus - mcts_bonus),
                "q_value": q,
                "confidence": confidence,
                "q_bonus": q_bonus,
                "mcts_score": mcts_score.mean_value if mcts_score else 0.0,
                "mcts_visits": mcts_score.visits if mcts_score else 0,
                "mcts_bonus": mcts_bonus,
                "memory_hit": False,
                "final_score": item["final_score"],
            })
        return sorted(out, key=lambda item: item["final_score"], reverse=True)
