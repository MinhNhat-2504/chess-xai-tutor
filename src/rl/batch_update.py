"""Batch Q-update từ Replay Buffer — Báo cáo mục 3.6.3.

Bản đồ án gốc gọi `replay.add(...)` sau mỗi nước nhưng KHÔNG BAO GIỜ `sample()`
ra để học lại — replay buffer bị bỏ phí. Module này cung cấp hàm
`batch_update` để sample mini-batch transitions và áp dụng lại công thức
Bellman, giúp:

- Tận dụng dữ liệu (mỗi transition được dùng nhiều lần).
- Giảm tương quan thời gian giữa các update (off-policy review).
- Tăng tốc độ hội tụ của Q-value với cùng số ván self-play.

Mỗi mini-batch là một list transitions `(s, a, r, s_next, next_actions)` lấy
ngẫu nhiên từ `ReplayBuffer.sample(batch_size)`.
"""
from __future__ import annotations


def batch_update(q, replay, batch_size: int, iterations: int = 1) -> int:
    """Sample `iterations` mini-batch và update Q-table cho từng transition.

    Trả về tổng số transition đã được update (để log/debug).
    """
    if batch_size <= 0 or iterations <= 0 or len(replay) == 0:
        return 0
    total = 0
    for _ in range(iterations):
        batch = replay.sample(batch_size)
        for (s, a, r, s_next, next_actions) in batch:
            q.update(s, a, r, s_next, next_actions)
            total += 1
    return total
