from src.board.chess_env import ChessEnv
from src.agents.alphabeta_agent import AlphaBetaAgent
from src.agents.minimax_agent import MinimaxAgent
from src.evaluation.evaluator import evaluate
from src.search.alphabeta import SearchStats, alphabeta
from src.search.move_ordering import order_moves
from src.search.transposition import TranspositionTable
import chess
import math

def test_alphabeta_returns_legal_move():
    env = ChessEnv()
    move = AlphaBetaAgent(depth=2).choose_move(env)
    assert move in env.legal_moves()


def test_evaluation_perspective_is_stable():
    env = ChessEnv()
    assert evaluate(env.board, chess.WHITE) == -evaluate(env.board, chess.BLACK)


def test_minimax_uses_root_perspective():
    env = ChessEnv("k7/8/8/8/8/8/7q/K6R w - - 0 1")
    assert MinimaxAgent(depth=1).choose_move(env).uci() == "h1h2"


def test_move_ordering_prioritizes_high_value_capture():
    board = chess.Board("4k3/8/8/8/8/8/3q4/3R3K w - - 0 1")
    ordered = order_moves(board, list(board.legal_moves))
    assert ordered[0].uci() == "d1d2"


def test_alphabeta_records_pruning_or_cache_stats():
    env = ChessEnv()
    stats = SearchStats()
    alphabeta(env, 3, -math.inf, math.inf, True, evaluate, stats, chess.WHITE, TranspositionTable())
    assert stats.visited > 0
    assert stats.pruned >= 0
    assert stats.cache_hits >= 0
