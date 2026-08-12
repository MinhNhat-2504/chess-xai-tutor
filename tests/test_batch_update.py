"""Test cho batch Q-update từ ReplayBuffer — Báo cáo mục 3.6.3."""
from src.rl.batch_update import batch_update
from src.rl.q_learning import QLearning
from src.rl.replay import ReplayBuffer


def _seed_replay(transitions, seed=0):
    rb = ReplayBuffer(capacity=1000, seed=seed)
    for t in transitions:
        rb.add(t)
    return rb


def test_batch_update_reuses_transitions_to_push_q_values():
    """Mỗi transition `(s,a,r)` cho cùng cặp (s,a) — sau N batch update,
    Q(s,a) phải dịch về phía `r`."""
    q = QLearning(alpha=0.5, gamma=0.0, seed=1)
    transitions = [("s", "a", 1.0, "s2", []) for _ in range(50)]
    rb = _seed_replay(transitions)

    n = batch_update(q, rb, batch_size=8, iterations=10)
    assert n == 80  # 8 transitions × 10 iterations
    # Sau nhiều update với alpha=0.5, gamma=0, target=r=1.0 → Q hội tụ về ~1.0
    assert q.get("s", "a") > 0.9


def test_batch_update_noop_when_replay_empty():
    q = QLearning()
    rb = ReplayBuffer(seed=0)
    assert batch_update(q, rb, batch_size=8, iterations=3) == 0


def test_batch_update_noop_when_disabled():
    q = QLearning()
    rb = _seed_replay([("s", "a", 1.0, "s2", [])] * 5)
    assert batch_update(q, rb, batch_size=0, iterations=3) == 0
    assert batch_update(q, rb, batch_size=8, iterations=0) == 0
    assert q.get("s", "a") == 0.0  # Q không đổi


def test_batch_update_distinguishes_actions():
    """2 cặp (s,a) khác nhau với reward đối nhau — sau batch update,
    Q values phản ánh được chiều khác nhau."""
    q = QLearning(alpha=0.3, gamma=0.0, seed=2)
    transitions = (
        [("s", "good", 1.0, "s2", [])] * 30
        + [("s", "bad", -1.0, "s2", [])] * 30
    )
    rb = _seed_replay(transitions, seed=2)
    batch_update(q, rb, batch_size=16, iterations=20)

    assert q.get("s", "good") > 0.5
    assert q.get("s", "bad") < -0.5
