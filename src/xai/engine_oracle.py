"""Oracle Stockfish cho lớp XAI.

``docs/XAI.md`` ghi rõ hạn chế của phiên bản đầu: điểm số lấy từ evaluator tự
viết ở độ sâu thấp nên kết luận chất lượng nước đi không đáng tin (1.e4 từng bị
gắn nhãn "thiếu chính xác"). Module này bọc một engine UCI chuẩn (Stockfish)
qua ``chess.engine`` để làm nguồn sự thật cho: điểm số, nước tốt nhất, top
phương án (MultiPV) và biến chính (PV). Phần *diễn giải* — phân rã 8 thành
phần, sự kiện chiến thuật, câu tiếng Việt — vẫn thuộc về ``MoveExplainer``.

Thứ tự dò tìm engine: đường dẫn truyền vào → biến môi trường ``STOCKFISH_PATH``
→ ``stockfish`` trên PATH → ``engines/stockfish/`` trong repo.
"""
from __future__ import annotations

import os
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Any

import chess
import chess.engine

# Điểm chiếu hết được ép về ±MATE_SCORE để so sánh được với centipawn thường.
MATE_SCORE = 10_000

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def find_stockfish(explicit_path: str | Path | None = None) -> Path | None:
    """Trả đường dẫn Stockfish đầu tiên tìm thấy, hoặc ``None``."""
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env_path = os.environ.get("STOCKFISH_PATH")
    if env_path:
        candidates.append(Path(env_path))
    on_path = shutil.which("stockfish")
    if on_path:
        candidates.append(Path(on_path))
    candidates.append(_PROJECT_ROOT / "engines" / "stockfish" / "stockfish.exe")
    candidates.append(_PROJECT_ROOT / "engines" / "stockfish" / "stockfish")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


class StockfishOracle:
    """Phiên phân tích Stockfish dùng lại được cho nhiều nước đi.

    Không thread-safe: mỗi luồng phân tích cần một oracle riêng. Nhớ gọi
    :meth:`close` (hoặc dùng ``with``) để tắt tiến trình engine.
    """

    def __init__(
        self,
        engine_path: str | Path | None = None,
        depth: int = 12,
        multipv: int = 3,
        threads: int = 2,
        hash_mb: int = 128,
        time_limit_s: float | None = 1.0,
        cache_size: int = 64,
    ):
        path = find_stockfish(engine_path)
        if path is None:
            raise FileNotFoundError(
                "Không tìm thấy Stockfish. Đặt STOCKFISH_PATH, thêm vào PATH, "
                "hoặc chép engine vào engines/stockfish/."
            )
        self.path = path
        self.depth = max(1, depth)
        self.multipv = max(1, multipv)
        # Nắp thời gian mỗi lần tìm kiếm: depth cố định đôi khi "nổ" ở tàn cuộc
        # (một thế mất 10-15s); dừng ở depth HOẶC hết giờ, cái nào tới trước.
        self.time_limit_s = time_limit_s
        # Cache theo FEN: khi phân tích cả ván, thế sau nước đi chính là thế của
        # nước kế tiếp — dùng lại để mỗi vị trí chỉ chạy engine đúng một lần.
        self._cache: "OrderedDict[str, list[dict[str, Any]]]" = OrderedDict()
        self._cache_size = max(0, cache_size)
        self.engine = chess.engine.SimpleEngine.popen_uci(str(path))
        try:
            self.engine.configure({"Threads": threads, "Hash": hash_mb})
        except chess.engine.EngineError:
            pass  # engine không có option tương ứng thì giữ mặc định
        self.name = self.engine.id.get("name", "Stockfish")

    def analyze(self, board: chess.Board, played: chess.Move | None = None) -> dict[str, Any]:
        """Chấm top MultiPV của vị trí và (nếu có) nước ``played``.

        Mọi điểm số theo góc nhìn của bên sắp đi tại ``board``, đơn vị
        centipawn, chiếu hết quy về ±``MATE_SCORE``.

        Nếu ``played`` không nằm trong top MultiPV, điểm của nó lấy từ phân tích
        thế cờ *sau* nước đó (cách Lichess làm) — kết quả này được cache nên
        khi phân tích nước kế tiếp không tốn thêm lần chạy engine nào.
        """
        pov = board.turn
        candidates = self._candidates(board, pov)

        played_entry = None
        if played is not None:
            played_entry = next((c for c in candidates if c["move"] == played.uci()), None)
            if played_entry is None:
                played_entry = self._played_from_next_position(board, played, pov)

        return {
            "name": self.name,
            "depth": self.depth,
            "candidates": candidates,
            "played": played_entry,
        }

    def _limit(self) -> chess.engine.Limit:
        if self.time_limit_s:
            return chess.engine.Limit(depth=self.depth, time=self.time_limit_s)
        return chess.engine.Limit(depth=self.depth)

    def _candidates(self, board: chess.Board, pov: chess.Color) -> list[dict[str, Any]]:
        """Top MultiPV của ``board`` theo góc nhìn ``pov`` (có cache theo FEN)."""
        key = board.fen()
        cached = self._cache.get(key)
        if cached is None:
            if board.is_game_over():
                cached = []
            else:
                infos = self.engine.analyse(board, self._limit(), multipv=self.multipv)
                cached = [e for e in (self._entry(info, board.turn) for info in infos) if e["move"]]
            self._remember(key, cached)
        else:
            self._cache.move_to_end(key)
        if pov == board.turn:
            return [dict(e) for e in cached]
        return [self._flip(e) for e in cached]

    def _played_from_next_position(self, board: chess.Board, played: chess.Move, pov: chess.Color) -> dict[str, Any]:
        after = board.copy(stack=False)
        after.push(played)
        if after.is_checkmate():
            return {"move": played.uci(), "score": float(MATE_SCORE), "mate": 1, "pv": [played]}
        if after.is_game_over():
            return {"move": played.uci(), "score": 0.0, "mate": None, "pv": [played]}
        reply = self._candidates(after, pov)  # đã quy về góc nhìn của bên vừa đi
        if not reply:
            return {"move": played.uci(), "score": 0.0, "mate": None, "pv": [played]}
        best_reply = reply[0]
        return {
            "move": played.uci(),
            "score": best_reply["score"],
            "mate": best_reply["mate"],
            "pv": [played, *best_reply["pv"]],
        }

    def _remember(self, key: str, value: list[dict[str, Any]]) -> None:
        if self._cache_size <= 0:
            return
        self._cache[key] = value
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    @staticmethod
    def _flip(entry: dict[str, Any]) -> dict[str, Any]:
        """Đổi góc nhìn điểm số sang bên kia (điểm và mate đổi dấu)."""
        return {
            "move": entry["move"],
            "score": -entry["score"],
            "mate": None if entry["mate"] is None else -entry["mate"],
            "pv": list(entry["pv"]),
        }

    @staticmethod
    def _entry(info: dict[str, Any], pov: chess.Color) -> dict[str, Any]:
        score = info["score"].pov(pov)
        pv = list(info.get("pv", []))
        return {
            "move": pv[0].uci() if pv else None,
            "score": float(score.score(mate_score=MATE_SCORE)),
            "mate": score.mate(),
            "pv": pv,
        }

    def close(self) -> None:
        if self.engine is not None:
            try:
                self.engine.quit()
            except chess.engine.EngineError:
                pass
            self.engine = None

    def __enter__(self) -> "StockfishOracle":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
