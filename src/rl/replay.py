"""Lưu trữ kinh nghiệm self-play — Báo cáo mục 3.6.3, 4.3.1."""
from collections import deque
import random


class ReplayBuffer:
    def __init__(self, capacity=100_000, seed=None):
        self.buffer = deque(maxlen=capacity)
        self.rng = random.Random(seed)

    def add(self, transition):  # (s, a, r, s_next, next_actions)
        self.buffer.append(transition)

    def sample(self, batch_size: int):
        size = min(batch_size, len(self.buffer))
        return self.rng.sample(list(self.buffer), size)

    def stats(self) -> dict[str, int]:
        return {"size": len(self.buffer), "capacity": self.buffer.maxlen or len(self.buffer)}

    def __len__(self):
        return len(self.buffer)
