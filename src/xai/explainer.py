"""XAI trung thực cho engine cờ vua trong project.

Lớp này kết hợp các loại bằng chứng có thể kiểm tra được:

* **Oracle**: khi máy có Stockfish, điểm số, nước tốt nhất, top phương án
  (MultiPV) và biến chính (PV) lấy từ Stockfish — chuẩn như các trang phân
  tích. Khi không có, tự động rơi về Alpha-Beta + evaluator của project.
* **Attribution**: điểm evaluator được tách thành vật chất, cơ động, an toàn
  vua, trung tâm, cấu trúc tốt, phát triển và đe doạ.
* **Counterfactual**: cùng một vị trí, chấm các nước thay thế để đo tổn thất
  của nước đã đi so với nước tốt nhất.
* **Tactical facts**: bắt quân, chiếu, nhập thành, phong cấp và quân treo.
* **Motif chiến thuật có tên**: đòn đôi (fork), ghim (pin), đòn xiên (skewer),
  đòn mở (discovered attack/check), chiếu hết tầng cuối — phát hiện bằng luật
  cờ thuần trong ``motifs.py``. Với nước sai và có oracle, hệ thống soi cả
  motif mà nước đó *cho phép đối thủ* thực hiện trong biến trừng phạt.

Không dùng mô hình ngôn ngữ để bịa lý do. Mọi câu kết luận đều sinh từ các số
điểm hoặc luật cờ ở trên. Chất lượng nước đi (best/blunder...) theo nguồn điểm
đang dùng; phần phân rã thành phần luôn dựa trên evaluator nội bộ nên chỉ mang
tính gợi ý sư phạm.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import chess

from ..agents.alphabeta_agent import AlphaBetaAgent
from ..board.chess_env import ChessEnv
from ..evaluation.evaluator import evaluate_breakdown
from ..evaluation.piece_tables import PIECE_VALUES
from .engine_oracle import StockfishOracle
from .game_summary import win_chance_from_cp as _win_chance
from .motifs import PIECE_NAMES_VI, detect_motifs


_PIECE_NAMES = PIECE_NAMES_VI
_COMPONENT_LABELS = {
    "material_position": "vật chất/vị trí quân",
    "mobility": "độ cơ động",
    "king_safety": "an toàn vua",
    "center_control": "kiểm soát trung tâm",
    "pawn_structure": "cấu trúc tốt",
    "development": "phát triển quân",
    "threats": "các quân đang bị treo",
    "check_pressure": "sức ép chiếu",
}


@dataclass(frozen=True)
class MoveQuality:
    label: str
    vietnamese: str


def _quality(loss: float) -> MoveQuality:
    # Ngưỡng theo centipawn (tốt = 100), tương thích cả Stockfish lẫn evaluator nội bộ.
    if loss <= 15:
        return MoveQuality("best", "nước tốt nhất")
    if loss <= 45:
        return MoveQuality("good", "nước tốt")
    if loss <= 100:
        return MoveQuality("inaccuracy", "thiếu chính xác")
    if loss <= 250:
        return MoveQuality("mistake", "sai lầm")
    return MoveQuality("blunder", "blunder")


class MoveExplainer:
    """Phân tích nước đi theo góc nhìn của người sắp đi.

    Mặc định thử dùng Stockfish (``use_stockfish=True``, tự dò đường dẫn);
    không có thì rơi về Alpha-Beta nội bộ với ``depth`` đã cho. ``engine_depth``
    là độ sâu Stockfish — 12–16 đủ tin cậy cho mục đích học cờ mà vẫn nhanh.

    Oracle giữ một tiến trình Stockfish chạy nền: gọi :meth:`close` (hoặc dùng
    ``with``) khi phân tích xong.
    """

    def __init__(
        self,
        depth: int = 2,
        use_quiescence: bool = True,
        q_max_depth: int = 6,
        use_stockfish: bool = True,
        engine_path: str | None = None,
        engine_depth: int = 14,
        multipv: int = 5,
    ):
        self.depth = max(1, depth)
        self.use_quiescence = use_quiescence
        self.q_max_depth = q_max_depth
        self.oracle: StockfishOracle | None = None
        if use_stockfish:
            try:
                self.oracle = StockfishOracle(
                    engine_path=engine_path, depth=engine_depth, multipv=multipv
                )
            except (FileNotFoundError, OSError, chess.engine.EngineError):
                self.oracle = None  # im lặng rơi về engine nội bộ

    @property
    def engine_label(self) -> str:
        if self.oracle is not None:
            return f"{self.oracle.name} (depth {self.oracle.depth})"
        return f"Alpha-Beta nội bộ (depth {self.depth})"

    def close(self) -> None:
        if self.oracle is not None:
            self.oracle.close()

    def __enter__(self) -> "MoveExplainer":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def analyze_move(self, board: chess.Board, move: chess.Move | str) -> dict[str, Any]:
        """Giải thích ``move`` trước khi nước đó được đẩy vào ``board``."""
        board_before = board.copy(stack=False)
        candidate = chess.Move.from_uci(move) if isinstance(move, str) else move
        if candidate not in board_before.legal_moves:
            raise ValueError(f"Illegal move for this position: {candidate.uci()}")

        perspective = board_before.turn
        san = board_before.san(candidate)
        if self.oracle is not None:
            scored = self._oracle_scores(board_before, candidate)
        else:
            scored = self._fallback_scores(board_before, candidate)
        loss = max(0.0, scored["best_score"] - scored["actual_score"])
        quality = _quality(loss)

        before = evaluate_breakdown(board_before, perspective)
        facts_before = self._hanging_pieces(board_before, perspective)
        captured = self._captured_piece(board_before, candidate)
        board_after = board_before.copy(stack=False)
        board_after.push(candidate)
        after = evaluate_breakdown(board_after, perspective)
        deltas = {
            key: after.get(key, 0.0) - before.get(key, 0.0)
            for key in set(before) | set(after)
            if key not in {"total", "terminal"}
        }
        best_san = self._san_for_uci(board_before, scored["best_move_uci"])
        motifs = detect_motifs(board_before, candidate)
        tactical_facts = [m.description_vi for m in motifs]
        tactical_facts += self._tactical_facts(board_before, candidate, board_after, captured, facts_before)
        reasons = self._component_reasons(deltas)
        refutation = scored["extras"].get("refutation_san", "")
        opponent_motifs = scored["extras"].get("opponent_motifs", [])
        text = self._narrative(
            san, quality, loss, best_san, reasons, tactical_facts, refutation, opponent_motifs
        )

        report = {
            "fen": board_before.fen(),
            "side": "white" if perspective == chess.WHITE else "black",
            "move_uci": candidate.uci(),
            "move_san": san,
            "quality": quality.label,
            "quality_vi": quality.vietnamese,
            "centipawn_loss": round(loss, 2),
            "score": round(scored["actual_score"], 2),
            "best_move_uci": scored["best_move_uci"],
            "best_move_san": best_san,
            "best_score": round(scored["best_score"], 2),
            "candidate_count": scored["candidate_count"],
            "top_candidates": scored["top_candidates"],
            "evaluation_before": self._rounded(before),
            "evaluation_after": self._rounded(after),
            "component_deltas": self._rounded(deltas),
            "reasons": reasons,
            "tactical_facts": tactical_facts,
            "motifs": [m.to_dict() for m in motifs],
            "explanation_vi": text,
            "method": scored["method"],
        }
        report.update(scored["extras"])
        return report

    def analyze_game(self, moves: Iterable[chess.Move], starting_fen: str | None = None) -> list[dict[str, Any]]:
        """Trả báo cáo cho từng ply của một ván; ``moves`` không bị thay đổi."""
        board = chess.Board(starting_fen) if starting_fen else chess.Board()
        report = []
        for ply, move in enumerate(moves, start=1):
            row = self.analyze_move(board, move)
            row["ply"] = ply
            row["move_number"] = board.fullmove_number
            report.append(row)
            board.push(move)
        return report

    def suggest_move(self, board: chess.Board) -> dict[str, Any] | None:
        """Gợi ý nước tốt nhất kèm biến chính — dùng cho màn chơi trực tiếp."""
        board = board.copy(stack=False)
        if board.is_game_over():
            return None
        if self.oracle is not None:
            result = self.oracle.analyze(board)
            if not result["candidates"]:
                return None
            best = result["candidates"][0]
            return {
                "move_uci": best["move"],
                "move_san": self._san_for_uci(board, best["move"]),
                "score": round(best["score"], 2),
                "win_chance": _win_chance(best["score"]),
                "line_san": self._line_san(board, best["pv"][:6]),
                "engine": result["name"],
            }
        candidates = self._candidates(board)
        if not candidates:
            return None
        best = candidates[0]
        return {
            "move_uci": best["move"],
            "move_san": self._san_for_uci(board, best["move"]),
            "score": round(float(best["final_score"]), 2),
            "win_chance": None,
            "line_san": "",
            "engine": "project Alpha-Beta",
        }

    # ------------------------------------------------------------------
    # Hai nguồn điểm số: Stockfish oracle và Alpha-Beta nội bộ
    # ------------------------------------------------------------------

    def _oracle_scores(self, board: chess.Board, candidate: chess.Move) -> dict[str, Any]:
        result = self.oracle.analyze(board, candidate)
        candidates = result["candidates"]
        played = result["played"]
        best = candidates[0] if candidates else played
        top_candidates = [
            {
                "move_uci": item["move"],
                "move_san": self._san_for_uci(board, item["move"]),
                "score": round(item["score"], 2),
                "line_san": self._line_san(board, item["pv"][:6]),
            }
            for item in candidates[:3]
        ]
        # PV của nước đã đi bắt đầu bằng chính nước đó; phần sau là cách đối
        # thủ đáp trả tốt nhất — với nước sai, đây chính là đòn trừng phạt.
        board_after = board.copy(stack=False)
        board_after.push(candidate)
        refutation_san = self._line_san(board_after, played["pv"][1:7])
        opponent_motifs = []
        if len(played["pv"]) > 1:
            opponent_motifs = detect_motifs(board_after, played["pv"][1])
        extras: dict[str, Any] = {
            "best_line_san": self._line_san(board, best["pv"][:8]),
            "refutation_san": refutation_san,
            "opponent_motifs": [m.to_dict() for m in opponent_motifs],
            "win_chance": _win_chance(played["score"]),
            "win_chance_best": _win_chance(best["score"]),
        }
        if played["mate"] is not None:
            extras["mate_in"] = played["mate"]
        scored_moves = {item["move"] for item in candidates} | {played["move"]}
        return {
            "actual_score": played["score"],
            "best_move_uci": best["move"],
            "best_score": best["score"],
            "top_candidates": top_candidates,
            "candidate_count": len(scored_moves),
            "extras": extras,
            "method": {
                "engine": result["name"],
                "depth": result["depth"],
                "multipv": self.oracle.multipv,
                "attribution": "evaluator nội bộ 8 thành phần (chỉ dùng cho phần diễn giải)",
                "limitation": (
                    "Điểm số, nước tốt nhất và biến chính lấy từ Stockfish. "
                    "Phần phân rã thành phần và câu giải thích dựa trên evaluator "
                    "nội bộ nên mang tính gợi ý sư phạm, không phải lý do của Stockfish."
                ),
            },
        }

    def _fallback_scores(self, board: chess.Board, candidate: chess.Move) -> dict[str, Any]:
        candidates = self._candidates(board)
        scores = {item["move"]: float(item["final_score"]) for item in candidates}
        best = candidates[0]
        return {
            "actual_score": scores[candidate.uci()],
            "best_move_uci": best["move"],
            "best_score": float(best["final_score"]),
            "top_candidates": [self._candidate_view(board, item) for item in candidates[:3]],
            "candidate_count": len(candidates),
            "extras": {},
            "method": {
                "engine": "project Alpha-Beta + handcrafted evaluator",
                "depth": self.depth,
                "quiescence": self.use_quiescence,
                "limitation": (
                    "Đây là giải thích cho evaluator hiện tại, không phải phân tích Stockfish. "
                    "Kết luận có thể thay đổi khi tăng độ sâu hoặc thay evaluator."
                ),
            },
        }

    def _candidates(self, board: chess.Board) -> list[dict[str, Any]]:
        agent = AlphaBetaAgent(
            depth=self.depth,
            use_transposition=True,
            use_quiescence=self.use_quiescence,
            q_max_depth=self.q_max_depth,
            use_killer_moves=True,
            use_history_heuristic=True,
        )
        agent.choose_move(ChessEnv(board.fen()))
        return sorted((dict(item) for item in agent.last_candidates), key=lambda item: item["final_score"], reverse=True)

    @staticmethod
    def _captured_piece(board: chess.Board, move: chess.Move) -> chess.Piece | None:
        if not board.is_capture(move):
            return None
        if board.is_en_passant(move):
            return chess.Piece(chess.PAWN, not board.turn)
        return board.piece_at(move.to_square)

    @staticmethod
    def _hanging_pieces(board: chess.Board, color: chess.Color) -> set[int]:
        return {
            square for square, piece in board.piece_map().items()
            if piece.color == color
            and piece.piece_type != chess.KING
            and board.attackers(not color, square)
            and not board.attackers(color, square)
        }

    def _tactical_facts(self, before, move, after, captured, hanging_before) -> list[str]:
        facts = []
        mover = before.piece_at(move.from_square)
        if captured is not None:
            facts.append(f"bắt {self._piece_name(captured)} (+{PIECE_VALUES[captured.piece_type]} điểm vật chất danh nghĩa)")
        if before.is_castling(move):
            facts.append("nhập thành, đưa vua về vị trí an toàn hơn và kích hoạt xe")
        if move.promotion:
            facts.append(f"phong cấp thành {_PIECE_NAMES[move.promotion]}")
        if after.is_checkmate():
            facts.append("chiếu hết")
        elif after.is_check():
            facts.append("tạo chiếu, buộc đối thủ phải trả lời")
        if mover is not None:
            attacked = len(after.attackers(not mover.color, move.to_square))
            defended = len(after.attackers(mover.color, move.to_square))
            if mover.piece_type != chess.KING and attacked and not defended:
                facts.append(f"nhưng {_PIECE_NAMES[mover.piece_type]} ở {chess.square_name(move.to_square)} đang bị treo")
        new_hanging = self._hanging_pieces(after, before.turn) - hanging_before
        if new_hanging:
            names = ", ".join(self._piece_at(after, square) for square in sorted(new_hanging)[:2])
            facts.append(f"làm xuất hiện quân treo: {names}")
        return facts

    @staticmethod
    def _piece_name(piece: chess.Piece) -> str:
        return _PIECE_NAMES[piece.piece_type]

    @staticmethod
    def _piece_at(board: chess.Board, square: int) -> str:
        piece = board.piece_at(square)
        return f"{_PIECE_NAMES[piece.piece_type]} {chess.square_name(square)}" if piece else chess.square_name(square)

    @staticmethod
    def _component_reasons(deltas: dict[str, float]) -> list[dict[str, Any]]:
        significant = [(key, value) for key, value in deltas.items() if abs(value) >= 2.0]
        significant.sort(key=lambda item: abs(item[1]), reverse=True)
        return [
            {"factor": key, "label_vi": _COMPONENT_LABELS.get(key, key), "delta": round(value, 2),
             "direction": "improved" if value > 0 else "worsened"}
            for key, value in significant[:3]
        ]

    @staticmethod
    def _narrative(san, quality, loss, best_san, reasons, facts, refutation="", opponent_motifs=()) -> str:
        fact_text = "; ".join(facts[:2]) if facts else "không tạo thay đổi chiến thuật tức thời nổi bật"
        reason_text = "; ".join(
            f"{item['label_vi']} {'tăng' if item['delta'] > 0 else 'giảm'} {abs(item['delta']):.0f}"
            for item in reasons[:2]
        ) or "tác động chủ yếu nằm trong biến thể đối thủ đáp trả"
        if quality.label in {"best", "good"}:
            return f"{san} là {quality.vietnamese}. {fact_text}. Theo evaluator: {reason_text}."
        text = (
            f"{san} là {quality.vietnamese}, kém nước {best_san} khoảng {loss:.0f} điểm. "
            f"{fact_text}. Dấu hiệu chính: {reason_text}."
        )
        if opponent_motifs:
            labels = ", ".join(dict.fromkeys(m["label_vi"] for m in opponent_motifs))
            text += f" Nước này mở đường cho đối thủ tạo {labels}."
        if refutation:
            text += f" Đối thủ có thể trừng phạt bằng: {refutation}."
        return text

    @staticmethod
    def _san_for_uci(board: chess.Board, move_uci: str) -> str:
        return board.san(chess.Move.from_uci(move_uci))

    @staticmethod
    def _line_san(board: chess.Board, moves: list[chess.Move]) -> str:
        """Diễn giải một biến thành chuỗi SAN có số nước (vd: ``1. e4 e5 2. Nf3``)."""
        if not moves:
            return ""
        return board.variation_san(moves)

    def _candidate_view(self, board: chess.Board, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "move_uci": item["move"],
            "move_san": self._san_for_uci(board, item["move"]),
            "score": round(float(item["final_score"]), 2),
        }

    @staticmethod
    def _rounded(values: dict[str, float]) -> dict[str, float]:
        return {key: round(float(value), 2) for key, value in values.items()}
