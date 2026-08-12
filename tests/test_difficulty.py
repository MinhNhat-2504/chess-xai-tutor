import chess

from src.agents.alphabeta_agent import AlphaBetaAgent
from src.agents.difficulty_agent import (
    DifficultyAgent,
    DifficultyProfile,
    build_difficulty_profile,
)
from src.board.chess_env import ChessEnv


class FixedCandidateAgent:
    def __init__(self):
        self.last_candidates = []
        self.last_stats = None
        self.last_info = None
        self.last_explanation = None

    def choose_move(self, env):
        self.last_candidates = [
            {"move": "e2e4", "final_score": 100.0},
            {"move": "d2d4", "final_score": 80.0},
            {"move": "g1f3", "final_score": 60.0},
        ]
        self.last_explanation = self.last_candidates[0]
        return chess.Move.from_uci("e2e4")


def test_hard_profile_keeps_best_candidate():
    env = ChessEnv()
    profile = DifficultyProfile(
        name="hard",
        label="Hard",
        target_elo=1500,
        temperature_cp=0.0,
        noise_cp=0.0,
        blunder_rate=0.0,
    )
    agent = DifficultyAgent(FixedCandidateAgent(), profile, seed=1)

    move = agent.choose_move(env)

    assert move.uci() == "e2e4"
    assert agent.last_explanation["difficulty_rank"] == 1


def test_blunder_profile_can_pick_lower_ranked_move():
    env = ChessEnv()
    profile = DifficultyProfile(
        name="easy",
        label="Easy",
        target_elo=900,
        temperature_cp=0.0,
        noise_cp=0.0,
        blunder_rate=1.0,
        blunder_pool=3,
    )
    agent = DifficultyAgent(FixedCandidateAgent(), profile, seed=2)

    move = agent.choose_move(env)

    assert move.uci() in {"d2d4", "g1f3"}
    assert agent.last_explanation["difficulty_rank"] > 1


def test_profile_can_be_loaded_from_config_shape():
    profile = build_difficulty_profile(
        "easy",
        {"profiles": {"easy": {"target_elo": 850, "depth": 1, "noise_cp": 10}}},
    )

    assert profile.target_elo == 850
    assert profile.depth == 1
    assert profile.noise_cp == 10


def test_difficulty_agent_wraps_real_search_agent():
    env = ChessEnv()
    profile = DifficultyProfile(
        name="hard",
        label="Hard",
        target_elo=1500,
        temperature_cp=0.0,
        noise_cp=0.0,
        blunder_rate=0.0,
    )
    agent = DifficultyAgent(AlphaBetaAgent(depth=1), profile, seed=1)

    move = agent.choose_move(env)

    assert move in env.legal_moves()
    assert agent.last_candidates
    assert agent.last_explanation["difficulty"] == "hard"
