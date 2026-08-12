from src.rl.q_learning import QLearning
from src.rl.replay import ReplayBuffer
from src.agents.hybrid_agent import HybridAgent
from src.board.chess_env import ChessEnv

def test_q_update_moves_value():
    q = QLearning(alpha=0.5, gamma=0.0)
    q.update("s", "a", 1.0, "s2", ["b"])
    assert q.get("s", "a") == 0.5


def test_q_update_without_quantization_keeps_float_value():
    q = QLearning(alpha=1.0, gamma=0.0, q_value_step=None)
    q.update("s", "a", 0.333, "s2", [])
    assert q.get("s", "a") == 0.333


def test_q_update_quantizes_to_step():
    q = QLearning(alpha=1.0, gamma=0.0, q_value_step=0.05)
    q.update("s", "a", 0.333, "s2", [])
    assert abs(q.get("s", "a") - 0.35) < 1e-9


def test_q_update_clips_before_quantization():
    q = QLearning(alpha=1.0, gamma=0.0, q_value_step=0.05, q_value_clip=0.2)
    q.update("s", "a", 1.0, "s2", [])
    assert abs(q.get("s", "a") - 0.2) < 1e-9


def test_q_select_exploitation_uses_best_value():
    q = QLearning(epsilon=0.0, seed=1)
    q.update("s", "good", 2.0, "s2", [])
    q.update("s", "bad", -1.0, "s2", [])
    assert q.select("s", ["bad", "good"]) == "good"


def test_q_save_and_load(tmp_path):
    path = tmp_path / "q.pkl"
    q = QLearning(alpha=1.0, gamma=0.0)
    q.update("s", "a", 3.0, "s2", [])
    q.save(path)

    loaded = QLearning()
    loaded.load(path)
    assert loaded.get("s", "a") == 3.0
    assert loaded.count("s", "a") == 1


def test_replay_sample_respects_batch_size():
    replay = ReplayBuffer(capacity=3, seed=1)
    replay.add(("s1", "a", 0, "s2", []))
    replay.add(("s2", "a", 0, "s3", []))
    assert len(replay.sample(10)) == 2


def test_hybrid_uses_injected_state_key_fn():
    class RecordingQ:
        def __init__(self):
            self.seen_states = []

        def get(self, s, a):
            self.seen_states.append(s)
            return 0.0

    q = RecordingQ()
    agent = HybridAgent(q, depth=1, lam=0.0, state_key_fn=lambda board: "compact-key")
    env = ChessEnv()
    assert agent.choose_move(env) in env.legal_moves()
    assert q.seen_states
    assert set(q.seen_states) == {"compact-key"}


def test_q_confidence_increases_with_update_count():
    q = QLearning(alpha=1.0, gamma=0.0)
    assert q.confidence("s", "a", k=2.0) == 0.0
    q.update("s", "a", 1.0, "s2", [])
    q.update("s", "a", 1.0, "s2", [])
    assert abs(q.confidence("s", "a", k=2.0) - 0.5) < 1e-9


def test_hybrid_explanation_contains_confidence_bonus():
    q = QLearning(alpha=1.0, gamma=0.0)
    q.update("fixed-state", "g1f3", 1.0, "s2", [])
    agent = HybridAgent(
        q,
        depth=1,
        lam=0.5,
        state_key_fn=lambda board: "fixed-state",
        use_confidence=True,
        confidence_k=1.0,
    )
    env = ChessEnv()
    assert agent.choose_move(env) in env.legal_moves()
    assert agent.last_explanation is not None
    assert {"alphabeta_score", "q_value", "confidence", "q_bonus", "final_score"} <= set(agent.last_explanation)
