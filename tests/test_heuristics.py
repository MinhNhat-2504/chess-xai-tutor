"""Test KillerTable + HistoryTable — Báo cáo mục 2.4.2 (mở rộng)."""
import chess

from src.search.heuristics import KillerTable, HistoryTable
from src.search.move_ordering import order_moves
from src.agents.alphabeta_agent import AlphaBetaAgent
from src.board.chess_env import ChessEnv


def test_killer_keeps_two_per_ply_and_dedups():
    kt = KillerTable()
    kt.add(3, "a1a2")
    kt.add(3, "a1a2")  # trùng — không thêm
    kt.add(3, "b1b2")
    kt.add(3, "c1c2")  # đẩy "a1a2" ra
    killers = kt.get(3)
    assert len(killers) == 2
    assert "c1c2" in killers
    assert "b1b2" in killers
    assert "a1a2" not in killers


def test_history_accumulates_depth_squared():
    ht = HistoryTable()
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")  # tốt e2 đi e4
    ht.add(board, move, depth=3)
    ht.add(board, move, depth=5)
    # PAWN tới e4: 3² + 5² = 34
    assert ht.score(board, move) == 9 + 25


def test_order_moves_promotes_killer_above_other_quiets():
    """Trong vị trí không có capture, killer move được đẩy lên trên các quiet khác."""
    # Vị trí: trắng có nhiều nước quiet, chọn 1 làm "killer"
    board = chess.Board()  # vị trí khởi đầu — toàn quiet move
    legal = list(board.legal_moves)
    # Chọn nước "a2a3" làm killer (quiet move không gây check)
    killer_uci = "a2a3"
    ordered = order_moves(board, legal, killers=(killer_uci,))
    # Killer phải nằm trong nhóm đầu (trước phần lớn các quiet khác)
    killer_idx = next(i for i, m in enumerate(ordered) if m.uci() == killer_uci)
    # Không phải số 1 nhất định vì có thể vài nước gives_check vẫn ở trên,
    # nhưng phải nằm trong top 5 ở vị trí khởi đầu có 20 quiet moves.
    assert killer_idx < 5


def test_history_breaks_tie_among_quiets():
    """Trong tập quiet move toàn-điểm-bằng-0, history bonus đẩy nước có history cao lên trên."""
    board = chess.Board()
    legal = list(board.legal_moves)
    ht = HistoryTable()
    # Cho nước g1f3 history score lớn
    favored = chess.Move.from_uci("g1f3")
    for _ in range(20):
        ht.add(board, favored, depth=5)  # 20 × 25 = 500

    ordered = order_moves(board, legal, history=ht)
    favored_idx = ordered.index(favored)
    assert favored_idx <= 3  # trong top 4


def test_agent_with_heuristics_still_returns_legal_move():
    """Smoke test: bật killer + history vẫn cho ra nước hợp lệ."""
    env = ChessEnv()
    agent = AlphaBetaAgent(
        depth=2,
        use_transposition=True,
        use_killer_moves=True,
        use_history_heuristic=True,
    )
    move = agent.choose_move(env)
    assert move in env.legal_moves()
