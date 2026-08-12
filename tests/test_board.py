from src.board.chess_env import ChessEnv
import chess

def test_initial_legal_moves():
    assert len(ChessEnv().legal_moves()) == 20


def test_reset_restores_initial_fen():
    env = ChessEnv()
    env.push(chess.Move.from_uci("e2e4"))
    env.reset()
    assert len(env.legal_moves()) == 20
    assert env.board.fullmove_number == 1


def test_castling_moves_are_legal():
    env = ChessEnv("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    moves = {move.uci() for move in env.legal_moves()}
    assert {"e1g1", "e1c1"} <= moves


def test_promotion_move_is_legal():
    env = ChessEnv("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    moves = {move.uci() for move in env.legal_moves()}
    assert "a7a8q" in moves


def test_en_passant_move_is_legal():
    env = ChessEnv("7k/8/8/3pPp2/8/8/8/4K3 w - f6 0 1")
    moves = {move.uci() for move in env.legal_moves()}
    assert "e5f6" in moves
