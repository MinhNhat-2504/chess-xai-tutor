"""Test cho Quiescence Search — Báo cáo mục 2.4.3."""
import math
import chess

from src.board.chess_env import ChessEnv
from src.evaluation.evaluator import evaluate
from src.search.alphabeta import SearchStats
from src.search.quiescence import quiescence
from src.agents.alphabeta_agent import AlphaBetaAgent


def test_quiescence_sees_recapture_after_queen_capture():
    """Sau khi trắng Qxe7+, đen sẽ Kxe7 ăn lại hậu.

    `evaluate` thuần (depth=0) chỉ thấy trắng đang dư hậu → ~+900 cho trắng.
    Quiescence kéo dài tìm kiếm trên các nước "ồn" → thấy mất hậu, trả ~0.
    """
    env = ChessEnv("4k3/4Q3/8/8/8/8/8/7K b - - 0 1")

    naive = evaluate(env.board, chess.WHITE)
    assert naive > 500  # trắng dư hậu

    stats = SearchStats()
    q_value = quiescence(env, -math.inf, math.inf, evaluate, stats, chess.WHITE, 0, 6)

    assert q_value < naive - 500  # quiescence phải thấy mất hậu
    assert stats.q_visited > 0


def test_quiescence_avoids_horizon_blunder_at_depth_1():
    """Ở depth=1: không quiescence sẽ chọn Qxe7+ (mất hậu lấy tốt);
    có quiescence sẽ tránh nước đó."""
    fen = "4k3/4p3/8/8/8/8/8/4Q2K w - - 0 1"
    blunder_uci = "e1e7"

    agent_no_q = AlphaBetaAgent(depth=1, use_quiescence=False)
    move_no_q = agent_no_q.choose_move(ChessEnv(fen))

    agent_with_q = AlphaBetaAgent(depth=1, use_quiescence=True)
    move_with_q = agent_with_q.choose_move(ChessEnv(fen))

    assert move_no_q.uci() == blunder_uci, \
        f"baseline không-quiescence phải chọn nước thí hậu (got {move_no_q.uci()})"
    assert move_with_q.uci() != blunder_uci, \
        f"có quiescence không được chọn nước thí hậu (got {move_with_q.uci()})"


def test_quiescence_respects_q_max_depth():
    """q_max_depth giới hạn được số node quiescence để tránh bùng nổ."""
    env = ChessEnv()  # vị trí khởi đầu, không có capture
    stats = SearchStats()
    quiescence(env, -math.inf, math.inf, evaluate, stats, chess.WHITE, 0, q_max_depth=2)
    assert stats.q_visited >= 1
    assert stats.q_visited < 1000  # vị trí khởi đầu không có capture nên rất bé


def test_quiescence_returns_legal_value_for_quiet_position():
    """Vị trí "yên tĩnh" (không có nước ồn) → quiescence trả về stand-pat."""
    env = ChessEnv()  # vị trí khởi đầu — không có capture/promotion/check
    stats = SearchStats()
    q_value = quiescence(env, -math.inf, math.inf, evaluate, stats, chess.WHITE, 0, 6)
    direct = evaluate(env.board, chess.WHITE)
    assert q_value == direct
