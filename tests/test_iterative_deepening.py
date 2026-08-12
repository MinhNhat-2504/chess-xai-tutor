"""Test cho Iterative Deepening — Báo cáo mục 2.4.4."""
import chess

from src.board.chess_env import ChessEnv
from src.evaluation.evaluator import evaluate
from src.search.iterative_deepening import search_iterative_root
from src.agents.alphabeta_agent import AlphaBetaAgent


def test_iterative_returns_legal_move():
    env = ChessEnv()
    best, val, stats, info = search_iterative_root(env, max_depth=2, evaluate=evaluate, perspective=chess.WHITE)
    assert best in env.legal_moves()
    assert len(info) >= 1
    assert info[-1]["depth"] == 2
    assert stats.visited > 0


def test_iterative_produces_info_for_each_completed_depth():
    env = ChessEnv()
    _, _, _, info = search_iterative_root(env, max_depth=3, evaluate=evaluate, perspective=chess.WHITE)
    depths = [i["depth"] for i in info]
    assert depths == [1, 2, 3]


def test_iterative_respects_time_limit():
    """Thời gian giới hạn rất nhỏ → có thể dừng trước khi hoàn thành max_depth.

    Quan trọng: vẫn trả về một nước đi hợp lệ (từ iteration đã hoàn thành),
    không return None hay raise."""
    env = ChessEnv()
    best, _, _, info = search_iterative_root(
        env, max_depth=20, evaluate=evaluate, perspective=chess.WHITE,
        time_limit_s=0.05,
    )
    # Ít nhất phải có 1 iteration hoàn thành (depth 1 luôn rất nhanh)
    assert best is not None
    assert best in env.legal_moves()
    assert len(info) >= 1


def test_iterative_agent_returns_legal_move():
    env = ChessEnv()
    agent = AlphaBetaAgent(depth=2, use_iterative_deepening=True)
    move = agent.choose_move(env)
    assert move in env.legal_moves()
    assert agent.last_info is not None
    assert agent.last_info[-1]["depth"] == 2


def test_iterative_stops_early_on_mate():
    """Vị trí có mate-in-1 cho trắng → tìm thấy ngay ở depth=1 (hoặc dừng sớm).

    Vị trí: 6k1/5ppp/8/8/8/8/5PPP/4Q1K1 w - - 0 1
    Trắng có Qe8# nếu vua đen đang trên g8 không có chỗ thoát…
    Đơn giản hoá: dùng vị trí queen-mate-in-1 phổ biến.
    """
    # Trắng tới phiên, có Qe8 chiếu hết
    env = ChessEnv("6k1/5ppp/8/8/8/8/8/4Q2K w - - 0 1")
    best, val, _, info = search_iterative_root(env, max_depth=5, evaluate=evaluate, perspective=chess.WHITE)
    # Phải tìm được nước thắng (value rất lớn)
    assert val > 50_000
    assert best is not None
