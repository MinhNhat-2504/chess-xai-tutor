"""Lưu trữ ván đã phân tích và bài tập cá nhân (SQLite, thư viện chuẩn).

Ba bảng:

* ``games`` — mỗi ván một dòng: PGN, header, phân tích từng nước (JSON) và tổng
  kết. Khoá là ``<source>:<id>`` nên nhập lại không phân tích trùng.
* ``puzzles`` — bài tập sinh từ lỗi trong ván (mỗi sai lầm/blunder có đòn trừng
  phạt = một bài "tìm đòn trừng phạt"), kèm lịch **ôn ngắt quãng** kiểu Leitner:
  đúng thì giãn ra (1 → 3 → 7 → 14 → 30 → 60 ngày), sai thì về 1 ngày.
* ``users`` — bảng nhỏ nhớ nguồn/tên người chơi đã nhập.

Mọi hàm nhận/trả dict thuần để web và test dùng thẳng. Một kết nối mỗi lần gọi
(``check_same_thread=False`` không cần vì mỗi lệnh mở/đóng riêng) — đủ cho một
người dùng local hoặc vài người trên server nhỏ.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .game_import import player_color

_ERROR_QUALITIES = ("mistake", "blunder")
_INTERVALS_DAYS = (1, 3, 7, 14, 30, 60)
_DAY = 86_400


_TACTICAL_HINTS = ("ăn ", "chiếu", "đòn", "ghim", "phong cấp", "đe doạ")


def _is_tactical_answer(first_step: dict, report: dict) -> bool:
    """Bài tập chỉ đáng làm khi nước trừng phạt đầu tiên có yếu tố chiến thuật
    (ăn quân, chiếu, đòn đôi/ghim/xiên/mở, đe doạ) — nước yên lặng dạy được ít."""
    if report.get("opponent_motifs"):
        return True
    note = (first_step.get("note") or "").lower()
    if any(hint in note for hint in _TACTICAL_HINTS):
        return float(report.get("centipawn_loss", 0)) >= 100
    return False


class TutorStore:
    def __init__(self, path: str | Path = "data/tutor.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    username TEXT NOT NULL,
                    user_color TEXT,
                    white TEXT, black TEXT, result TEXT, date TEXT,
                    time_class TEXT, opening TEXT, url TEXT,
                    pgn TEXT NOT NULL,
                    analysis_json TEXT,
                    summary_json TEXT,
                    engine TEXT,
                    analyzed_at REAL
                );
                CREATE INDEX IF NOT EXISTS idx_games_user ON games(username, source);
                CREATE TABLE IF NOT EXISTS puzzles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    game_id TEXT NOT NULL,
                    ply INTEGER NOT NULL,
                    fen TEXT NOT NULL,
                    solver TEXT NOT NULL,
                    blunder_san TEXT, blunder_by TEXT, quality TEXT,
                    answer_uci TEXT NOT NULL, answer_san TEXT,
                    line_json TEXT, motif TEXT, headline TEXT,
                    box INTEGER DEFAULT 0, due_at REAL, reviews INTEGER DEFAULT 0,
                    correct INTEGER DEFAULT 0, last_result TEXT, created_at REAL,
                    UNIQUE(username, game_id, ply)
                );
                CREATE INDEX IF NOT EXISTS idx_puzzles_due ON puzzles(username, due_at);
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT NOT NULL, source TEXT NOT NULL, last_import REAL,
                    PRIMARY KEY (username, source)
                );
                """
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------ games
    def has_analysis(self, game_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT analysis_json FROM games WHERE id=?", (game_id,)).fetchone()
        return bool(row and row["analysis_json"])

    def save_game(self, game: dict[str, Any], username: str, analysis: list[dict], summary: dict, engine: str) -> None:
        headers = {"White": game.get("white", ""), "Black": game.get("black", "")}
        color = player_color(headers, username)
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO games
                   (id, source, username, user_color, white, black, result, date, time_class, opening, url,
                    pgn, analysis_json, summary_json, engine, analyzed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    game["id"], game["source"], username.strip().lower(), color,
                    game.get("white", ""), game.get("black", ""), game.get("result", "*"), game.get("date", ""),
                    game.get("time_class", ""), game.get("opening", ""), game.get("url", ""),
                    game["pgn"], json.dumps(analysis, ensure_ascii=False), json.dumps(summary, ensure_ascii=False),
                    engine, time.time(),
                ),
            )
            conn.execute(
                "INSERT OR REPLACE INTO users(username, source, last_import) VALUES (?,?,?)",
                (username.strip().lower(), game["source"], time.time()),
            )
        self._create_puzzles(username, game["id"], color, analysis)

    def list_games(self, username: str, source: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT id, source, user_color, white, black, result, date, time_class, opening, url, summary_json, engine, analyzed_at FROM games WHERE username=?"
        args: list[Any] = [username.strip().lower()]
        if source:
            sql += " AND source=?"
            args.append(source)
        sql += " ORDER BY date DESC, analyzed_at DESC"
        with self._conn() as conn:
            rows = conn.execute(sql, args).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["summary"] = json.loads(item.pop("summary_json") or "null")
            out.append(item)
        return out

    def get_game(self, game_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["analysis"] = json.loads(item.pop("analysis_json") or "[]")
        item["summary"] = json.loads(item.pop("summary_json") or "null")
        return item

    def known_users(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT username, source, last_import FROM users ORDER BY last_import DESC").fetchall()
        return [dict(r) for r in rows]

    # ---------------------------------------------------------- puzzles
    def _create_puzzles(self, username: str, game_id: str, user_color: str | None, analysis: list[dict]) -> int:
        """Mỗi sai lầm/blunder có đòn trừng phạt → một bài 'tìm đòn trừng phạt'.

        Người giải là bên *được* trừng phạt (đối thủ của người vừa đi sai). Bài
        từ lỗi của chính bạn dạy bạn nhìn thấy đòn mình để hở; bài từ lỗi của đối
        thủ dạy bạn không bỏ lỡ cơ hội.
        """
        created = 0
        now = time.time()
        with self._conn() as conn:
            for report in analysis:
                if report.get("quality") not in _ERROR_QUALITIES:
                    continue
                line = report.get("refutation_line") or []
                if not line:
                    continue
                if not _is_tactical_answer(line[0], report):
                    continue  # nước đáp yên lặng thì không thành bài "tìm đòn trừng phạt"
                solver = "black" if report["side"] == "white" else "white"
                blunder_by = "you" if user_color == report["side"] else "opponent"
                motifs = report.get("opponent_motifs") or []
                motif = motifs[0]["label_vi"] if motifs else ""
                fen_after = report.get("fen_after")
                if not fen_after:
                    continue
                cur = conn.execute(
                    """INSERT OR IGNORE INTO puzzles
                       (username, game_id, ply, fen, solver, blunder_san, blunder_by, quality,
                        answer_uci, answer_san, line_json, motif, headline, box, due_at, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?)""",
                    (
                        username.strip().lower(), game_id, report.get("ply", 0), fen_after, solver,
                        report.get("move_san", ""), blunder_by, report.get("quality", ""),
                        line[0]["move_uci"], line[0].get("move_san", ""),
                        json.dumps(line, ensure_ascii=False), motif, report.get("headline_vi", ""),
                        now, now,
                    ),
                )
                created += cur.rowcount
        return created

    def puzzle_stats(self, username: str) -> dict[str, Any]:
        now = time.time()
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM puzzles WHERE username=?", (username.strip().lower(),)).fetchone()[0]
            due = conn.execute("SELECT COUNT(*) FROM puzzles WHERE username=? AND due_at<=?", (username.strip().lower(), now)).fetchone()[0]
            mastered = conn.execute("SELECT COUNT(*) FROM puzzles WHERE username=? AND box>=4", (username.strip().lower(),)).fetchone()[0]
        return {"total": total, "due": due, "mastered": mastered}

    def next_puzzle(self, username: str, allow_not_due: bool = True) -> dict[str, Any] | None:
        now = time.time()
        user = username.strip().lower()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM puzzles WHERE username=? AND due_at<=? ORDER BY due_at ASC, id ASC LIMIT 1", (user, now)
            ).fetchone()
            if row is None and allow_not_due:
                row = conn.execute(
                    "SELECT * FROM puzzles WHERE username=? ORDER BY due_at ASC, id ASC LIMIT 1", (user,)
                ).fetchone()
        return self._puzzle_view(row, now) if row else None

    def get_puzzle(self, puzzle_id: int) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM puzzles WHERE id=?", (puzzle_id,)).fetchone()
        return self._puzzle_view(row, time.time()) if row else None

    def record_answer(self, puzzle_id: int, correct: bool) -> dict[str, Any]:
        now = time.time()
        with self._conn() as conn:
            row = conn.execute("SELECT box, reviews, correct FROM puzzles WHERE id=?", (puzzle_id,)).fetchone()
            if row is None:
                raise KeyError(puzzle_id)
            box = min(row["box"] + 1, len(_INTERVALS_DAYS) - 1) if correct else 0
            due_at = now + _INTERVALS_DAYS[box] * _DAY
            conn.execute(
                "UPDATE puzzles SET box=?, due_at=?, reviews=reviews+1, correct=correct+?, last_result=? WHERE id=?",
                (box, due_at, 1 if correct else 0, "correct" if correct else "wrong", puzzle_id),
            )
        return {"box": box, "next_in_days": _INTERVALS_DAYS[box]}

    @staticmethod
    def _puzzle_view(row: sqlite3.Row, now: float) -> dict[str, Any]:
        item = dict(row)
        item["line"] = json.loads(item.pop("line_json") or "[]")
        item["is_due"] = (item.get("due_at") or 0) <= now
        return item
