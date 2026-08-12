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
        depth: int = 14,
        multipv: int = 5,
        threads: int = 2,
        hash_mb: int = 128,
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
        """
        pov = board.turn
        limit = chess.engine.Limit(depth=self.depth)
        infos = self.engine.analyse(board, limit, multipv=self.multipv)
        candidates = [entry for entry in (self._entry(info, pov) for info in infos) if entry["move"]]

        played_entry = None
        if played is not None:
            played_entry = next((c for c in candidates if c["move"] == played.uci()), None)
            if played_entry is None:
                info = self.engine.analyse(board, limit, root_moves=[played])
                played_entry = self._entry(info, pov)
                if played_entry["move"] is None:  # engine không trả PV (hiếm)
                    played_entry["move"] = played.uci()
                    played_entry["pv"] = [played]

        return {
            "name": self.name,
            "depth": self.depth,
            "candidates": candidates,
            "played": played_entry,
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
