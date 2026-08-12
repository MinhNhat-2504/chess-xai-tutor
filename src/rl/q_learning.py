"""Q-Learning — Báo cáo mục 2.5, 3.6.

Công thức cập nhật:
    Q(s,a) <- Q(s,a) + α [ r + γ·max_a' Q(s',a') − Q(s,a) ]
"""
import pickle
import random
from collections import defaultdict
from pathlib import Path


class QLearning:
    def __init__(self, alpha=0.1, gamma=0.95, epsilon=0.2,
                 epsilon_min=0.02, epsilon_decay=0.999, seed=None,
                 q_value_step=None, q_value_clip=None):
        self.q = defaultdict(float)          # (state_key, move_uci) -> value
        self.counts = defaultdict(int)       # (state_key, move_uci) -> update count
        self.alpha, self.gamma = alpha, gamma
        self.epsilon = epsilon
        self.epsilon_min, self.epsilon_decay = epsilon_min, epsilon_decay
        self.rng = random.Random(seed)
        self.q_value_step = q_value_step
        self.q_value_clip = q_value_clip
        if self.q_value_step is not None and self.q_value_step <= 0:
            raise ValueError("q_value_step must be positive or None.")
        if self.q_value_clip is not None and self.q_value_clip <= 0:
            raise ValueError("q_value_clip must be positive or None.")

    def get(self, s: str, a: str) -> float:
        return self.q.get((s, a), 0.0)

    def best_value(self, s: str, actions: list[str]) -> float:
        return max((self.get(s, a) for a in actions), default=0.0)

    def select(self, s: str, actions: list[str]) -> str:
        """Epsilon-greedy: cân bằng Exploration / Exploitation (mục 2.5.3)."""
        if not actions:
            raise ValueError("Cannot select an action from an empty action list.")
        if self.rng.random() < self.epsilon:
            return self.rng.choice(actions)
        best = self.best_value(s, actions)
        best_actions = [a for a in actions if self.get(s, a) == best]
        return self.rng.choice(best_actions)

    def update(self, s, a, r, s_next, next_actions):
        target = r + self.gamma * self.best_value(s_next, next_actions)
        value = self.q[(s, a)] + self.alpha * (target - self.q[(s, a)])
        self.q[(s, a)] = self._quantize_value(value)
        self.counts[(s, a)] += 1
        return self.q[(s, a)]

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump({"q": dict(self.q), "counts": dict(self.counts)}, f)

    def load(self, path):
        with Path(path).open("rb") as f:
            payload = pickle.load(f)
        if isinstance(payload, dict) and "q" in payload:
            self.q = defaultdict(float, payload.get("q", {}))
            self.counts = defaultdict(int, payload.get("counts", {}))
        else:
            self.q = defaultdict(float, payload)
            self.counts = defaultdict(int)

    def mean_abs_q(self) -> float:
        if not self.q:
            return 0.0
        return sum(abs(value) for value in self.q.values()) / len(self.q)

    def unique_states(self) -> int:
        return len({state for state, _ in self.q.keys()})

    def actions_per_state(self) -> float:
        states = self.unique_states()
        return len(self.q) / states if states else 0.0

    def _quantize_value(self, value: float) -> float:
        if self.q_value_clip is not None:
            value = max(-self.q_value_clip, min(self.q_value_clip, value))
        if self.q_value_step is not None:
            value = round(value / self.q_value_step) * self.q_value_step
        return value

    def count(self, s: str, a: str) -> int:
        return self.counts.get((s, a), 0)

    def confidence(self, s: str, a: str, k: float = 10.0) -> float:
        n = self.count(s, a)
        return n / (n + k) if n > 0 else 0.0
