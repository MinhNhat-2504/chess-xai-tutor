"""Huấn luyện Q-Learning bằng Self-play — Báo cáo mục 2.5.4, 4.3.

AI tự chơi với chính nó; mỗi nước đi sinh transition (s,a,r,s') để cập nhật Q.
Ghi lại diễn biến hội tụ Q-value qua các vòng (mục 4.3.2).

Bản nâng cấp:
- Sau mỗi ván, sample mini-batch từ replay buffer để **học lại off-policy**
  (mục 3.6.3) — bản cũ bỏ phí buffer.
- Bọc loop bằng `tqdm` cho progress bar.
- Cho phép inject `state_key_fn` để A/B test full FEN vs compact state (mục 3.6.1 mở rộng).
"""
import csv
from collections import Counter
from pathlib import Path
from typing import Callable

from ..board.chess_env import ChessEnv
from ..board.state import state_key as default_state_key
from ..evaluation.evaluator import evaluate
from ..rl.reward import move_reward, shaping_reward, terminal_reward
from ..rl.replay import ReplayBuffer
from ..rl.batch_update import batch_update


def self_play_game(
    q,
    env: ChessEnv,
    max_moves: int,
    replay: ReplayBuffer | None = None,
    state_key_fn: Callable = default_state_key,
):
    moves = 0
    total_reward = 0.0
    while not env.is_terminal() and moves < max_moves:
        s = state_key_fn(env.board)
        actions = [m.uci() for m in env.legal_moves()]
        a = q.select(s, actions)
        move = env.board.parse_uci(a)
        color = env.board.turn
        eval_before = evaluate(env.board, color)
        board_before = env.board.copy(stack=False)

        env.push_uci(a)
        s_next = state_key_fn(env.board)
        next_actions = [m.uci() for m in env.legal_moves()]
        eval_after = evaluate(env.board, color)
        reward = (
            terminal_reward(env.board, color)
            + shaping_reward(eval_before, eval_after)
            + move_reward(board_before, move, env.board)
        )

        q.update(s, a, reward, s_next, next_actions)
        if replay is not None:
            replay.add((s, a, reward, s_next, next_actions))
        total_reward += reward
        moves += 1

    q.decay_epsilon()
    result = env.result() if env.is_terminal() else "1/2-1/2"
    return {"result": result, "moves": moves, "total_reward": total_reward, "epsilon": q.epsilon}


def train(
    q,
    num_games,
    max_moves,
    save_every,
    q_table_path,
    history_path=None,
    batch_size: int = 0,
    batch_updates_per_game: int = 0,
    warmup_games: int = 0,
    state_key_fn: Callable = default_state_key,
    show_progress: bool = True,
):
    """Loop self-play self-improving.

    Args:
        batch_size: kích thước mini-batch lấy từ replay (0 = không dùng replay).
        batch_updates_per_game: số mini-batch áp dụng sau mỗi ván self-play.
        warmup_games: bao nhiêu ván đầu KHÔNG dùng replay batch (để tránh
            overfit reward-shaping noise sớm).
    """
    q_table_path = Path(q_table_path)
    q_table_path.parent.mkdir(parents=True, exist_ok=True)
    history_path = Path(history_path) if history_path else q_table_path.with_name("training_history.csv")
    replay = ReplayBuffer()
    history = []
    results = Counter()

    iterator = range(1, num_games + 1)
    if show_progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(iterator, desc="self-play", unit="game")
        except ImportError:
            pass

    for g in iterator:
        row = {"game": g, **self_play_game(q, ChessEnv(), max_moves, replay, state_key_fn), "replay_size": len(replay)}

        # Off-policy replay batch updates (sau warmup_games đầu)
        if (
            batch_size > 0
            and batch_updates_per_game > 0
            and g > warmup_games
            and len(replay) >= batch_size
        ):
            updated = batch_update(q, replay, batch_size, batch_updates_per_game)
            row["replay_updates"] = updated
        else:
            row["replay_updates"] = 0
        row.update(_q_metrics(q))

        history.append(row)
        results[row["result"]] += 1
        if g % save_every == 0:
            q.save(q_table_path)
            msg = (
                f"[self-play] game {g}/{num_games} | result={row['result']} "
                f"| |Q|={len(q.q)} | replay={len(replay)} | eps={q.epsilon:.3f} "
                f"| mean|Q|={q.mean_abs_q():.4f}"
            )
            if show_progress and hasattr(iterator, "write"):
                iterator.write(msg)
            else:
                print(msg)
    q.save(q_table_path)
    _write_history(history, history_path)
    print(f"[self-play] summary={dict(results)} | saved={q_table_path} | history={history_path}")
    return history


def _write_history(history, history_path: Path) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "game",
        "result",
        "moves",
        "total_reward",
        "q_size",
        "unique_states",
        "actions_per_state",
        "mean_abs_q",
        "epsilon",
        "replay_size",
        "replay_updates",
    ]
    with history_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in history:
            # Đảm bảo mọi field tồn tại (replay_updates có thể vắng ở bản cũ)
            writer.writerow({k: row.get(k, 0) for k in fieldnames})


def _q_metrics(q) -> dict[str, float]:
    q_size = len(q.q)
    unique_states = q.unique_states() if hasattr(q, "unique_states") else len({s for s, _ in q.q.keys()})
    return {
        "q_size": q_size,
        "unique_states": unique_states,
        "actions_per_state": q_size / unique_states if unique_states else 0.0,
        "mean_abs_q": q.mean_abs_q(),
    }
