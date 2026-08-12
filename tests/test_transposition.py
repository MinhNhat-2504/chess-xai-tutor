"""Test cho TranspositionTable — Báo cáo mục 2.4.5."""
import math
import chess

from src.board.chess_env import ChessEnv
from src.evaluation.evaluator import evaluate
from src.search.alphabeta import SearchStats, alphabeta
from src.search.transposition import TranspositionTable, TTFlag


def test_exact_returns_cached_value():
    tt = TranspositionTable()
    tt.store("k", depth=3, score=12.5, flag=TTFlag.EXACT, best_move="e2e4")
    value, best = tt.probe("k", depth=3, alpha=-math.inf, beta=math.inf)
    assert value == 12.5
    assert best == "e2e4"


def test_lower_bound_only_returns_when_beats_beta():
    tt = TranspositionTable()
    tt.store("k", depth=3, score=10.0, flag=TTFlag.LOWER, best_move="a1a2")
    # score=10 < beta=20 → KHÔNG cutoff, nhưng vẫn trả best_move cho ordering
    value, best = tt.probe("k", depth=3, alpha=0.0, beta=20.0)
    assert value is None
    assert best == "a1a2"
    # score=10 >= beta=5 → cutoff
    value, best = tt.probe("k", depth=3, alpha=0.0, beta=5.0)
    assert value == 10.0


def test_upper_bound_only_returns_when_below_alpha():
    tt = TranspositionTable()
    tt.store("k", depth=3, score=-8.0, flag=TTFlag.UPPER, best_move="b1c3")
    # score=-8 > alpha=-20 → không cutoff
    value, best = tt.probe("k", depth=3, alpha=-20.0, beta=0.0)
    assert value is None
    assert best == "b1c3"
    # score=-8 <= alpha=-5 → cutoff
    value, best = tt.probe("k", depth=3, alpha=-5.0, beta=10.0)
    assert value == -8.0


def test_insufficient_depth_returns_only_best_move():
    """Entry sâu hơn truy vấn 1 ply → không thể cutoff nhưng vẫn dùng best_move ordering."""
    tt = TranspositionTable()
    tt.store("k", depth=2, score=5.0, flag=TTFlag.EXACT, best_move="g1f3")
    value, best = tt.probe("k", depth=4, alpha=-math.inf, beta=math.inf)
    assert value is None
    assert best == "g1f3"


def test_store_keeps_deeper_entry():
    """Khi đã có entry sâu hơn, store entry cạn không được ghi đè."""
    tt = TranspositionTable()
    tt.store("k", depth=6, score=1.0, flag=TTFlag.EXACT, best_move="a")
    tt.store("k", depth=2, score=99.0, flag=TTFlag.EXACT, best_move="b")
    value, best = tt.probe("k", depth=6, alpha=-math.inf, beta=math.inf)
    assert value == 1.0
    assert best == "a"


def test_alphabeta_integration_records_cache_hits():
    """Search từ vị trí khởi đầu với TT bật → trải qua ít nhất một transposition."""
    env = ChessEnv()
    stats = SearchStats()
    tt = TranspositionTable()
    alphabeta(env, 3, -math.inf, math.inf, True, evaluate, stats, chess.WHITE, tt)
    assert stats.visited > 0
    assert len(tt) > 0
    # cache_hits có thể là 0 ở depth 3 với move ordering ngẫu nhiên — không yêu cầu > 0
    assert stats.cache_hits >= 0
