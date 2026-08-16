"""Test kho lưu ván/bài tập, hồ sơ điểm yếu và trình đọc API (không gọi mạng)."""
import json
import time

import chess

from src.xai import MoveExplainer
from src.xai.game_import import fetch_chesscom, fetch_lichess, player_color
from src.xai.profile import build_profile
from src.xai.store import TutorStore

# 5.Nxf7?? Qxg2 — ván ngắn có blunder rõ, dùng engine nội bộ depth 1 cho nhanh.
_PGN = '[White "me"]\n[Black "them"]\n[Result "0-1"]\n[Date "2026.08.10"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Nd4 4. Nxe5 Qg5 5. Nxf7 Qxg2 6. Rf1 Qxe4+ 7. Be2 Nf3# 0-1'


def _analyze(pgn):
    import io
    import chess.pgn
    from src.xai import summarize_game
    game = chess.pgn.read_game(io.StringIO(pgn))
    board = chess.Board()
    explainer = MoveExplainer(depth=1, use_stockfish=False)
    analysis = []
    for ply, move in enumerate(game.mainline_moves(), start=1):
        report = explainer.analyze_move(board, move)
        report["ply"] = ply
        report["move_number"] = board.fullmove_number
        board.push(move)
        report["fen_after"] = board.fen()
        # engine nội bộ không có refutation_line; giả lập để test bài tập
        if report["quality"] in ("mistake", "blunder"):
            nxt = list(board.legal_moves)[0]
            after = board.copy(); after.push(nxt)
            report["refutation_line"] = [{"label": "x", "move_uci": nxt.uci(), "move_san": board.san(nxt), "fen_after": after.fen(), "note": "đòn"}]
            report["opponent_motifs"] = [{"kind": "fork", "label_vi": "đòn đôi"}]
        analysis.append(report)
    return analysis, summarize_game(analysis), dict(game.headers)


def _game_dict(gid, headers):
    return {"id": gid, "source": "chesscom", "url": "", "white": headers["White"], "black": headers["Black"],
            "result": headers["Result"], "date": headers["Date"], "pgn": _PGN, "time_class": "blitz", "opening": "Italian Game"}


def test_store_saves_games_and_generates_puzzles(tmp_path):
    store = TutorStore(tmp_path / "t.db")
    analysis, summary, headers = _analyze(_PGN)
    assert not store.has_analysis("chesscom:1")
    store.save_game(_game_dict("chesscom:1", headers), "me", analysis, summary, "test-engine")
    assert store.has_analysis("chesscom:1")

    games = store.list_games("me")
    assert len(games) == 1 and games[0]["user_color"] == "white"
    full = store.get_game("chesscom:1")
    assert len(full["analysis"]) == len(analysis)
    assert store.known_users()[0]["username"] == "me"

    stats = store.puzzle_stats("me")
    assert stats["total"] >= 1 and stats["due"] == stats["total"]
    puzzle = store.next_puzzle("me")
    assert puzzle and puzzle["is_due"] and puzzle["answer_uci"]
    assert puzzle["blunder_by"] in ("you", "opponent")


def test_puzzle_spaced_repetition_schedule(tmp_path):
    store = TutorStore(tmp_path / "t.db")
    analysis, summary, headers = _analyze(_PGN)
    store.save_game(_game_dict("chesscom:2", headers), "me", analysis, summary, "e")
    puzzle = store.next_puzzle("me")
    first = store.record_answer(puzzle["id"], correct=True)
    assert first["box"] == 1 and first["next_in_days"] == 3
    again = store.get_puzzle(puzzle["id"])
    assert not again["is_due"] and again["reviews"] == 1 and again["correct"] == 1
    reset = store.record_answer(puzzle["id"], correct=False)
    assert reset["box"] == 0 and reset["next_in_days"] == 1
    # Không còn bài đến hạn -> vẫn trả bài để luyện thêm nếu cho phép
    assert store.next_puzzle("me", allow_not_due=False) is None or store.puzzle_stats("me")["due"] > 0
    assert store.next_puzzle("me", allow_not_due=True) is not None


def test_profile_only_counts_players_own_moves(tmp_path):
    store = TutorStore(tmp_path / "t.db")
    analysis, summary, headers = _analyze(_PGN)
    store.save_game(_game_dict("chesscom:3", headers), "me", analysis, summary, "e")
    store.save_game(_game_dict("chesscom:4", {**headers, "Date": "2026.08.11"}), "me", analysis, summary, "e")
    profile = build_profile([store.get_game(g["id"]) for g in store.list_games("me")])

    assert profile["games"] == 2
    assert profile["moves"] == 2 * len([r for r in analysis if r["side"] == "white"])
    assert profile["results"]["loss"] == 2  # "me" cầm trắng, ván 0-1
    assert profile["insights_vi"] and "Độ chính xác" in profile["insights_vi"][0]
    assert profile["openings"][0]["opening"] == "Italian Game"
    assert any(m["kind"] == "fork" for m in profile["motifs"])
    assert len(profile["accuracy_history"]) == 2


def test_profile_empty():
    assert build_profile([])["games"] == 0


def test_player_color():
    assert player_color({"White": "Alice", "Black": "bob"}, "alice") == "white"
    assert player_color({"White": "Alice", "Black": "bob"}, "BOB") == "black"
    assert player_color({"White": "Alice", "Black": "bob"}, "carol") is None


def test_fetch_chesscom_parses_archives_without_network():
    archives = {"archives": ["https://api.chess.com/pub/player/x/games/2026/07", "https://api.chess.com/pub/player/x/games/2026/08"]}
    month = {"games": [
        {"url": "https://www.chess.com/game/live/111", "pgn": _PGN, "rules": "chess", "time_class": "blitz",
         "white": {"username": "me"}, "black": {"username": "them"}},
        {"url": "https://www.chess.com/game/live/222", "pgn": _PGN, "rules": "chess960", "white": {"username": "me"}, "black": {"username": "z"}},
    ]}
    def fake_fetch(url, accept=None):
        return json.dumps(archives if url.endswith("/archives") else month)
    games = fetch_chesscom("x", max_games=5, fetch=fake_fetch)
    # 2 tháng x 1 ván chess (bỏ chess960) — tháng mới nhất trước
    assert [g.id for g in games] == ["chesscom:111", "chesscom:111"]
    assert games[0].white == "me" and games[0].result == "0-1" and games[0].time_class == "blitz"


def test_fetch_lichess_parses_pgn_stream_without_network():
    stream = '[Event "Rated Blitz game"]\n[Site "https://lichess.org/abc123"]\n[White "me"]\n[Black "them"]\n[Result "1-0"]\n[Date "2026.08.01"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5 2. Nf3 1-0\n\n' \
             '[Event "Rated Rapid game"]\n[Site "https://lichess.org/def456"]\n[White "them"]\n[Black "me"]\n[Result "0-1"]\n[Date "2026.08.02"]\n\n1. d4 d5 0-1\n'
    games = fetch_lichess("me", max_games=5, fetch=lambda url, accept=None: stream)
    assert [g.id for g in games] == ["lichess:abc123", "lichess:def456"]
    assert games[0].opening == "Sicilian Defense" and games[0].time_class == "game"
    assert "1. e4 c5" in games[0].pgn
