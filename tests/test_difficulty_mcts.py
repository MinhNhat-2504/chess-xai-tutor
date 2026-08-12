import chess

from src.agents.difficulty import DIFFICULTY_LABELS, build_difficulty_agent
from src.agents.hybrid_agent import HybridAgent
from src.board.chess_env import ChessEnv
from src.rl.q_learning import QLearning
from src.search.mcts import mcts_best_move, mcts_scores


def test_mcts_returns_root_scores_for_legal_moves():
    board = chess.Board()
    scores = mcts_scores(board, chess.WHITE, iterations=12, rollout_depth=2, seed=1)
    assert scores
    assert set(scores).issubset({move.uci() for move in board.legal_moves})
    assert all(score.visits > 0 for score in scores.values())


def test_mcts_best_move_is_legal():
    board = chess.Board()
    move = mcts_best_move(board, chess.WHITE, iterations=12, rollout_depth=2, seed=2)
    assert move in board.legal_moves


def test_difficulty_presets_return_legal_moves(tmp_path):
    assert DIFFICULTY_LABELS["hell"] == "Siêu khó địa ngục"
    for difficulty in ("easy", "medium"):
        agent = build_difficulty_agent(difficulty, q_table=tmp_path / "missing.pkl", search_cfg={"medium_depth": 2})
        env = ChessEnv()
        assert agent.choose_move(env) in env.legal_moves()


def test_hell_preset_uses_memory_and_time_budget(tmp_path):
    memory_path = tmp_path / "hell_memory.json"
    agent = build_difficulty_agent(
        "hell",
        q_table=tmp_path / "missing.pkl",
        search_cfg={
            "hell_depth": 1,
            "hell_min_depth": 1,
            "hell_time_limit_s": 0.05,
            "hell_mcts_iterations": 4,
            "hell_mcts_rollout_depth": 1,
            "hell_mcts_time_limit_s": 0.02,
            "hell_memory_path": memory_path,
        },
        seed=3,
    )
    env = ChessEnv()
    first = agent.choose_move(env)
    assert first in env.legal_moves()
    assert memory_path.exists()

    cached_agent = build_difficulty_agent(
        "hell",
        q_table=tmp_path / "missing.pkl",
        search_cfg={
            "hell_depth": 1,
            "hell_min_depth": 1,
            "hell_memory_path": memory_path,
        },
        seed=4,
    )
    cached = cached_agent.choose_move(ChessEnv())
    assert cached == first
    assert cached_agent.last_explanation["memory_hit"] is True
    assert cached_agent.last_stats.visited == 0


def test_hybrid_mcts_explanation_contains_mcts_fields():
    q = QLearning()
    agent = HybridAgent(
        q,
        depth=1,
        use_mcts=True,
        mcts_iterations=30,
        mcts_rollout_depth=2,
        mcts_weight=20.0,
    )
    env = ChessEnv()
    assert agent.choose_move(env) in env.legal_moves()
    assert agent.last_explanation["mcts_visits"] > 0
    assert "mcts_bonus" in agent.last_explanation


def test_hybrid_move_memory_reuses_seen_position(tmp_path):
    memory_path = tmp_path / "memory.json"
    q = QLearning()
    agent = HybridAgent(q, depth=1, enable_memory=True, memory_path=memory_path)
    env = ChessEnv()
    first = agent.choose_move(env)
    assert first in env.legal_moves()
    assert memory_path.exists()

    cached_agent = HybridAgent(q, depth=3, enable_memory=True, memory_path=memory_path)
    cached = cached_agent.choose_move(ChessEnv())
    assert cached == first
    assert cached_agent.last_explanation["memory_hit"] is True
    assert cached_agent.last_stats.visited == 0
