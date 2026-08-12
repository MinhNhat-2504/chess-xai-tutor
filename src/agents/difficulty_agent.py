"""Difficulty wrapper for controlled-strength play.

The wrapped engine still evaluates every legal root move. This layer only
decides how often the AI should choose a lower-ranked move, which makes the
strength easier to tune without weakening the search code itself.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import chess

from .base_agent import BaseAgent


@dataclass(frozen=True)
class DifficultyProfile:
    name: str
    label: str
    target_elo: int
    depth: int | None = None
    temperature_cp: float = 0.0
    noise_cp: float = 0.0
    blunder_rate: float = 0.0
    blunder_pool: int = 3
    candidate_pool: int | None = None
    search_overrides: dict = field(default_factory=dict)


DEFAULT_DIFFICULTY_PROFILES = {
    "easy": {
        "label": "Easy",
        "target_elo": 900,
        "depth": 1,
        "temperature_cp": 220.0,
        "noise_cp": 160.0,
        "blunder_rate": 0.30,
        "blunder_pool": 6,
        "candidate_pool": 8,
        "use_quiescence": False,
        "use_iterative_deepening": False,
        "use_killer_moves": False,
        "use_history_heuristic": False,
    },
    "medium": {
        "label": "Medium",
        "target_elo": 1200,
        "depth": 2,
        "temperature_cp": 90.0,
        "noise_cp": 55.0,
        "blunder_rate": 0.10,
        "blunder_pool": 4,
        "candidate_pool": 5,
        "use_quiescence": False,
        "use_iterative_deepening": False,
    },
    "hard": {
        "label": "Hard",
        "target_elo": 1550,
        "depth": 4,
        "temperature_cp": 0.0,
        "noise_cp": 0.0,
        "blunder_rate": 0.0,
        "blunder_pool": 2,
        "candidate_pool": 3,
        "use_quiescence": True,
        "use_iterative_deepening": False,
        "use_killer_moves": True,
        "use_history_heuristic": True,
    },
}

DIFFICULTY_NAMES = tuple(DEFAULT_DIFFICULTY_PROFILES.keys())
_SEARCH_OVERRIDE_KEYS = {
    "use_transposition",
    "use_quiescence",
    "q_max_depth",
    "use_iterative_deepening",
    "time_limit_s",
    "use_killer_moves",
    "use_history_heuristic",
}


def build_difficulty_profile(name: str, difficulty_cfg: dict | None = None) -> DifficultyProfile:
    profiles = _extract_profiles(difficulty_cfg)
    if name not in DEFAULT_DIFFICULTY_PROFILES and name not in profiles:
        raise ValueError(f"Unsupported difficulty: {name}")

    raw = dict(DEFAULT_DIFFICULTY_PROFILES.get(name, {}))
    raw.update(profiles.get(name, {}))
    search_overrides = {key: raw[key] for key in _SEARCH_OVERRIDE_KEYS if key in raw}
    return DifficultyProfile(
        name=name,
        label=str(raw.get("label", name.title())),
        target_elo=int(raw.get("target_elo", 0)),
        depth=raw.get("depth"),
        temperature_cp=float(raw.get("temperature_cp", raw.get("temperature", 0.0))),
        noise_cp=float(raw.get("noise_cp", 0.0)),
        blunder_rate=float(raw.get("blunder_rate", 0.0)),
        blunder_pool=int(raw.get("blunder_pool", 3)),
        candidate_pool=raw.get("candidate_pool"),
        search_overrides=search_overrides,
    )


def _extract_profiles(cfg: dict | None) -> dict:
    if not cfg:
        return {}
    if "difficulty" in cfg:
        return cfg.get("difficulty", {}).get("profiles", {}) or {}
    if "profiles" in cfg:
        return cfg.get("profiles", {}) or {}
    return cfg


class DifficultyAgent(BaseAgent):
    def __init__(self, base_agent: BaseAgent, profile: DifficultyProfile, seed=None):
        self.base_agent = base_agent
        self.profile = profile
        self.rng = random.Random(seed)
        self.last_candidates = []
        self.last_explanation = None
        self.last_stats = None
        self.last_info = None

    def choose_move(self, env) -> chess.Move | None:
        engine_move = self.base_agent.choose_move(env)
        self._copy_engine_metadata()
        candidates = self._normalize_candidates(env, getattr(self.base_agent, "last_candidates", []))
        if not candidates:
            return engine_move

        chosen = self._select(candidates)
        move = chess.Move.from_uci(chosen["move"])
        self.last_candidates = candidates
        self.last_explanation = {
            **chosen,
            "difficulty": self.profile.name,
            "target_elo": self.profile.target_elo,
        }
        return move if move in env.legal_moves() else engine_move

    def _copy_engine_metadata(self):
        self.last_stats = getattr(self.base_agent, "last_stats", None)
        self.last_info = getattr(self.base_agent, "last_info", None)
        self.last_explanation = getattr(self.base_agent, "last_explanation", None)
        self.last_candidates = getattr(self.base_agent, "last_candidates", [])

    def _normalize_candidates(self, env, candidates):
        legal_uci = {move.uci() for move in env.legal_moves()}
        normalized = []
        for item in candidates:
            move_uci = item.get("move") if isinstance(item, dict) else str(item)
            if move_uci not in legal_uci:
                continue
            row = dict(item) if isinstance(item, dict) else {"move": move_uci}
            row["move"] = move_uci
            row["difficulty_base_score"] = self._candidate_score(row)
            normalized.append(row)
        normalized.sort(key=lambda row: row["difficulty_base_score"], reverse=True)
        for index, row in enumerate(normalized, start=1):
            row["difficulty_rank"] = index
        return normalized

    @staticmethod
    def _candidate_score(candidate: dict) -> float:
        for key in ("final_score", "score", "alphabeta_score", "minimax_score"):
            if key in candidate:
                return float(candidate[key])
        return 0.0

    def _select(self, candidates):
        pool_size = self.profile.candidate_pool or len(candidates)
        pool = candidates[:max(1, min(pool_size, len(candidates)))]

        if self.profile.blunder_rate > 0 and len(pool) > 1:
            if self.rng.random() < self.profile.blunder_rate:
                end = max(2, min(self.profile.blunder_pool, len(pool)))
                return dict(self.rng.choice(pool[1:end]))

        scored = []
        for candidate in pool:
            score = candidate["difficulty_base_score"]
            if self.profile.noise_cp > 0:
                score += self.rng.gauss(0.0, self.profile.noise_cp)
            scored.append((score, candidate))

        if self.profile.temperature_cp <= 0:
            return dict(max(scored, key=lambda item: item[0])[1])

        best_score = max(score for score, _ in scored)
        weights = [
            math.exp((score - best_score) / self.profile.temperature_cp)
            for score, _ in scored
        ]
        return dict(self._weighted_choice(scored, weights))

    def _weighted_choice(self, scored, weights):
        total = sum(weights)
        if total <= 0:
            return max(scored, key=lambda item: item[0])[1]
        target = self.rng.random() * total
        cumulative = 0.0
        for (_, candidate), weight in zip(scored, weights):
            cumulative += weight
            if cumulative >= target:
                return candidate
        return scored[-1][1]
