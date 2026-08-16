"""Kéo ván đấu của một người chơi từ Chess.com hoặc Lichess qua API công khai.

Không cần đăng nhập hay API key — cả hai đều mở dữ liệu ván công khai. Chỉ dùng
``urllib`` trong thư viện chuẩn để không thêm phụ thuộc.

* Chess.com: ``/pub/player/<user>/games/archives`` → danh sách kho theo tháng
  → đọc từ tháng mới nhất lùi dần cho đủ số ván. Chess.com bắt buộc có
  ``User-Agent``.
* Lichess: ``/api/games/user/<user>?max=N`` với ``Accept: application/x-chess-pgn``
  trả về nhiều ván PGN nối tiếp nhau.

Mỗi ván trả về dạng :class:`ImportedGame` (PGN + vài header đã tách sẵn).
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any, Callable

import chess.pgn

USER_AGENT = "chess-xai-tutor/0.1 (+https://github.com/MinhNhat-2504/chess-xai-tutor)"
SOURCES = ("chesscom", "lichess")
_TIMEOUT = 25


class ImportError_(Exception):
    """Lỗi kéo ván có thông báo tiếng Việt cho người dùng."""


@dataclass
class ImportedGame:
    id: str            # "<source>:<id>"
    source: str
    url: str
    white: str
    black: str
    result: str
    date: str
    pgn: str
    time_class: str = ""
    opening: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fetch(url: str, accept: str | None = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ImportError_("Không tìm thấy người chơi này — kiểm tra lại tên và nguồn (Chess.com hay Lichess).") from exc
        if exc.code == 429:
            raise ImportError_("Bị giới hạn tốc độ tạm thời, thử lại sau một phút.") from exc
        raise ImportError_(f"Máy chủ trả lỗi {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise ImportError_("Không kết nối được tới máy chủ — kiểm tra mạng.") from exc


def _headers_from_pgn(pgn: str) -> dict[str, str]:
    game = chess.pgn.read_headers(io.StringIO(pgn))
    return dict(game) if game else {}


def fetch_chesscom(username: str, max_games: int = 30, fetch: Callable[..., str] = _fetch) -> list[ImportedGame]:
    username = username.strip().lower()
    archives = json.loads(fetch(f"https://api.chess.com/pub/player/{urllib.parse.quote(username)}/games/archives")).get("archives", [])
    games: list[ImportedGame] = []
    for archive_url in reversed(archives):
        payload = json.loads(fetch(archive_url))
        for raw in reversed(payload.get("games", [])):
            if raw.get("rules", "chess") != "chess" or not raw.get("pgn"):
                continue  # bỏ chess960/bughouse...
            headers = _headers_from_pgn(raw["pgn"])
            games.append(ImportedGame(
                id="chesscom:" + raw.get("url", "").rstrip("/").split("/")[-1],
                source="chesscom",
                url=raw.get("url", ""),
                white=raw.get("white", {}).get("username", headers.get("White", "?")),
                black=raw.get("black", {}).get("username", headers.get("Black", "?")),
                result=headers.get("Result", "*"),
                date=headers.get("Date", ""),
                pgn=raw["pgn"],
                time_class=raw.get("time_class", ""),
                opening=_opening_name(headers),
            ))
            if len(games) >= max_games:
                return games
    return games


def fetch_lichess(username: str, max_games: int = 30, fetch: Callable[..., str] = _fetch) -> list[ImportedGame]:
    username = username.strip()
    query = urllib.parse.urlencode({"max": max_games, "opening": "true", "clocks": "false", "evals": "false", "perfType": "ultraBullet,bullet,blitz,rapid,classical,correspondence"})
    text = fetch(f"https://lichess.org/api/games/user/{urllib.parse.quote(username)}?{query}", accept="application/x-chess-pgn")
    games: list[ImportedGame] = []
    stream = io.StringIO(text)
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        headers = dict(game.headers)
        exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
        pgn = game.accept(exporter)
        site = headers.get("Site", "")
        game_id = headers.get("GameId") or site.rstrip("/").split("/")[-1]
        games.append(ImportedGame(
            id=f"lichess:{game_id}",
            source="lichess",
            url=site,
            white=headers.get("White", "?"),
            black=headers.get("Black", "?"),
            result=headers.get("Result", "*"),
            date=headers.get("Date", headers.get("UTCDate", "")),
            pgn=pgn,
            time_class=headers.get("Event", "").split()[-1].lower() if headers.get("Event") else "",
            opening=headers.get("Opening", ""),
        ))
        if len(games) >= max_games:
            break
    return games


def _opening_name(headers: dict[str, str]) -> str:
    if headers.get("Opening"):
        return headers["Opening"]
    eco_url = headers.get("ECOUrl", "")
    if eco_url:
        slug = eco_url.rstrip("/").split("/")[-1]
        return slug.replace("-", " ")
    return headers.get("ECO", "")


def fetch_games(source: str, username: str, max_games: int = 30) -> list[ImportedGame]:
    """Kéo tối đa ``max_games`` ván mới nhất của ``username`` từ ``source``."""
    if not username or not username.strip():
        raise ImportError_("Hãy nhập tên người chơi.")
    max_games = max(1, min(int(max_games), 100))
    if source == "chesscom":
        return fetch_chesscom(username, max_games)
    if source == "lichess":
        return fetch_lichess(username, max_games)
    raise ImportError_("Nguồn không hợp lệ (chỉ hỗ trợ chesscom hoặc lichess).")


def player_color(game_headers: dict[str, str], username: str) -> str | None:
    """'white'/'black' nếu ``username`` chơi ván này, else None."""
    name = username.strip().lower()
    if game_headers.get("White", "").strip().lower() == name:
        return "white"
    if game_headers.get("Black", "").strip().lower() == name:
        return "black"
    return None
