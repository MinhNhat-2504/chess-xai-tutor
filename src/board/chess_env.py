"""Biểu diễn bàn cờ & sinh nước đi hợp lệ — Báo cáo mục 2.2, 3.3.

Bọc thư viện python-chess để xử lý: di chuyển, ăn quân, chiếu, chiếu hết,
và các luật đặc biệt (phong cấp, nhập thành, bắt tốt qua đường).
"""
import chess


class ChessEnv:
    def __init__(self, fen: str | None = None):
        self.initial_fen = fen
        self.board = chess.Board(fen) if fen else chess.Board()

    def reset(self, fen: str | None = None) -> None:
        """Đưa môi trường về vị trí ban đầu hoặc một FEN mới."""
        if fen is not None:
            self.initial_fen = fen
        self.board = chess.Board(self.initial_fen) if self.initial_fen else chess.Board()

    def copy(self) -> "ChessEnv":
        env = ChessEnv()
        env.initial_fen = self.initial_fen
        env.board = self.board.copy(stack=True)
        return env

    def legal_moves(self) -> list[chess.Move]:
        return list(self.board.legal_moves)

    def push(self, move: chess.Move) -> None:
        self.board.push(move)

    def push_uci(self, move_uci: str) -> chess.Move:
        move = chess.Move.from_uci(move_uci)
        if move not in self.board.legal_moves:
            raise ValueError(f"Illegal move for current position: {move_uci}")
        self.board.push(move)
        return move

    def pop(self) -> chess.Move:
        return self.board.pop()

    def is_terminal(self) -> bool:
        return self.board.is_game_over()

    def outcome(self) -> chess.Outcome | None:
        return self.board.outcome()

    def result(self) -> str:
        """'1-0', '0-1', '1/2-1/2' hoặc '*' nếu chưa kết thúc."""
        return self.board.result()

    def fen(self) -> str:
        return self.board.fen()

    def san(self, move: chess.Move) -> str:
        return self.board.san(move)
