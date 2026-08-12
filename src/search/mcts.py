"""Monte Carlo Tree Search for root move scoring.

MCTS here is used as an upgrade signal for the strongest demo difficulty:
it estimates root move quality by UCT selection, random tactical rollouts,
and heuristic evaluation when a rollout is truncated.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Optional

import chess

from ..evaluation.evaluator import evaluate


@dataclass
class MCTSMoveScore:
    move: chess.Move
    visits: int
    mean_value: float

    @property
    def confidence_score(self) -> float:
        return (self.mean_value + 1.0) / 2.0


@dataclass
class _Node:
    board: chess.Board
    move: Optional[chess.Move] = None
    parent: Optional["_Node"] = None
    children: list["_Node"] = field(default_factory=list)
    visits: int = 0
    value_sum: float = 0.0
    untried_moves: list[chess.Move] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.untried_moves:
            self.untried_moves = list(self.board.legal_moves)

    @property
    def fully_expanded(self) -> bool:
        return not self.untried_moves

    @property
    def mean_value(self) -> float:
        return self.value_sum / self.visits if self.visits else 0.0


def mcts_scores(
    board: chess.Board,
    perspective: bool,
    iterations: int = 300,
    rollout_depth: int = 18,
    exploration: float = math.sqrt(2.0),
    seed: int | None = None,
    time_limit_s: float | None = None,
) -> dict[str, MCTSMoveScore]:
    """Return MCTS estimates for legal root moves keyed by UCI."""
    if board.is_game_over() or iterations <= 0:
        return {}

    rng = random.Random(seed)
    root = _Node(board.copy(stack=False))
    deadline = time.perf_counter() + time_limit_s if time_limit_s else None

    for _ in range(iterations):
        if deadline is not None and time.perf_counter() >= deadline:
            break

        node = _select(root, exploration, rng, perspective)
        if node.untried_moves and not node.board.is_game_over():
            node = _expand(node, rng)
        reward = _rollout(node.board.copy(stack=False), perspective, rollout_depth, rng)
        _backpropagate(node, reward)

    return {
        child.move.uci(): MCTSMoveScore(child.move, child.visits, child.mean_value)
        for child in root.children
        if child.move is not None
    }


def mcts_best_move(
    board: chess.Board,
    perspective: bool,
    iterations: int = 300,
    rollout_depth: int = 18,
    seed: int | None = None,
) -> chess.Move | None:
    scores = mcts_scores(board, perspective, iterations=iterations, rollout_depth=rollout_depth, seed=seed)
    if not scores:
        return None
    return max(scores.values(), key=lambda score: (score.visits, score.mean_value)).move


def _select(node: _Node, exploration: float, rng: random.Random, perspective: bool) -> _Node:
    while node.fully_expanded and node.children and not node.board.is_game_over():
        maximizing = node.board.turn == perspective
        node = max(
            node.children,
            key=lambda child: _uct_score(child, exploration, rng, maximizing),
        )
    return node


def _expand(node: _Node, rng: random.Random) -> _Node:
    idx = rng.randrange(len(node.untried_moves))
    move = node.untried_moves.pop(idx)
    child_board = node.board.copy(stack=False)
    child_board.push(move)
    child = _Node(child_board, move=move, parent=node)
    node.children.append(child)
    return child


def _backpropagate(node: _Node, reward: float) -> None:
    while node is not None:
        node.visits += 1
        node.value_sum += reward
        node = node.parent


def _uct_score(node: _Node, exploration: float, rng: random.Random, maximizing: bool) -> float:
    if node.visits == 0:
        return math.inf
    parent_visits = max(1, node.parent.visits if node.parent else 1)
    exploit = node.mean_value if maximizing else -node.mean_value
    explore = exploration * math.sqrt(math.log(parent_visits + 1) / node.visits)
    return exploit + explore + rng.random() * 1e-9


def _rollout(board: chess.Board, perspective: bool, max_depth: int, rng: random.Random) -> float:
    for _ in range(max_depth):
        if board.is_game_over():
            return _terminal_reward(board, perspective)
        moves = list(board.legal_moves)
        if not moves:
            break
        board.push(_rollout_policy(board, moves, rng))

    if board.is_game_over():
        return _terminal_reward(board, perspective)
    return math.tanh(evaluate(board, perspective) / 1200.0)


def _rollout_policy(board: chess.Board, moves: list[chess.Move], rng: random.Random) -> chess.Move:
    tactical = [
        move
        for move in moves
        if board.is_capture(move) or move.promotion or board.gives_check(move)
    ]
    if tactical and rng.random() < 0.7:
        return rng.choice(tactical)
    return rng.choice(moves)


def _terminal_reward(board: chess.Board, perspective: bool) -> float:
    outcome = board.outcome()
    if outcome is None or outcome.winner is None:
        return 0.0
    return 1.0 if outcome.winner == perspective else -1.0
