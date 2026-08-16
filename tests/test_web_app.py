"""Test web UI: parse PGN, luồng phân tích qua API, vẽ bàn cờ SVG."""
import time

import chess
import pytest

from src.ui.web_app import create_app, parse_pgn


@pytest.fixture()
def client():
    # Fallback engine depth 1 để test nhanh và không phụ thuộc Stockfish.
    app = create_app(use_stockfish=False, fallback_depth=1)
    app.config["TESTING"] = True
    return app.test_client()


def test_parse_pgn_rejects_bad_input():
    with pytest.raises(ValueError):
        parse_pgn("")
    with pytest.raises(ValueError):
        parse_pgn("đây không phải PGN")


def test_parse_pgn_reads_sample_game():
    text = open("data/sample.pgn", encoding="utf-8").read()
    game, moves = parse_pgn(text)
    assert len(moves) >= 4
    assert moves[0] == chess.Move.from_uci("e2e4")


def test_index_page_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Chess XAI Tutor".encode() in response.data


def test_board_svg_endpoint(client):
    response = client.get("/board.svg?lastmove=e2e4")
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert client.get("/board.svg?fen=khong-hop-le").status_code == 400


def test_analyze_flow_returns_reports_and_summary(client):
    text = open("data/sample.pgn", encoding="utf-8").read()
    _, moves = parse_pgn(text)
    response = client.post("/api/analyze", data={"pgn": text})
    assert response.status_code == 200
    job = response.get_json()
    assert job["total"] == len(moves)

    deadline = time.time() + 60
    data = None
    while time.time() < deadline:
        data = client.get(f"/api/job/{job['job_id']}").get_json()
        if data["status"] in ("done", "error"):
            break
        time.sleep(0.2)

    assert data["status"] == "done"
    assert data["analyzed"] == len(moves)
    assert len(data["reports"]) == len(moves)
    first = data["reports"][0]
    assert first["move_san"] == "e4"
    assert "explanation_vi" in first
    assert "fen_after" in first
    assert any(line.startswith("Trắng") for line in data["summary_lines"])


def test_analyze_rejects_empty_pgn(client):
    response = client.post("/api/analyze", data={"pgn": "   "})
    assert response.status_code == 400
    assert "PGN" in response.get_json()["error"]


def test_job_not_found(client):
    assert client.get("/api/job/khongco").status_code == 404


def test_games_profile_puzzle_endpoints_with_empty_store(tmp_path):
    from src.ui.web_app import create_app as _create
    app = _create(use_stockfish=False, fallback_depth=1, db_path=tmp_path / "t.db")
    app.config["TESTING"] = True
    c = app.test_client()
    assert c.get("/api/games").get_json() == {"games": [], "users": []}
    assert c.get("/api/games?username=nobody").get_json()["games"] == []
    assert c.get("/api/profile?username=nobody").get_json()["games"] == 0
    assert c.get("/api/puzzles/next?username=nobody").get_json()["puzzle"] is None
    assert c.get("/api/games/khong-co").status_code == 404
    assert c.post("/api/import", data={"username": ""}).status_code == 400
    assert c.get("/board.svg?selected=e2").status_code == 200


def test_import_job_with_fake_fetch_creates_games_and_puzzles(tmp_path, monkeypatch):
    import json as _json
    from src.ui import web_app as wa
    pgn = '[White "me"]\n[Black "them"]\n[Result "0-1"]\n[Date "2026.08.10"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bc4 Nd4 4. Nxe5 Qg5 5. Nxf7 Qxg2 6. Rf1 Qxe4+ 7. Be2 Nf3# 0-1'
    from src.xai.game_import import ImportedGame
    monkeypatch.setattr(wa, "fetch_games", lambda source, username, max_games: [
        ImportedGame(id="chesscom:9", source="chesscom", url="", white="me", black="them", result="0-1", date="2026.08.10", pgn=pgn),
        ImportedGame(id="chesscom:10", source="chesscom", url="", white="a", black="b", result="1-0", date="2026.08.10", pgn=pgn),  # không phải ván của "me"
    ])
    app = wa.create_app(use_stockfish=False, fallback_depth=1, db_path=tmp_path / "t.db")
    app.config["TESTING"] = True
    c = app.test_client()
    job = c.post("/api/import", data={"source": "chesscom", "username": "me", "max": 5}).get_json()
    deadline = time.time() + 60
    while time.time() < deadline:
        status = c.get(f"/api/import/{job['job_id']}").get_json()
        if status["status"] != "running":
            break
        time.sleep(0.2)
    assert status["status"] == "done" and status["total"] == 1 and status["analyzed"] == 1
    games = c.get("/api/games?username=me").get_json()["games"]
    assert len(games) == 1 and games[0]["user_color"] == "white"
    profile = c.get("/api/profile?username=me").get_json()
    assert profile["games"] == 1
    # Nhập lại: bỏ qua ván đã có
    job2 = c.post("/api/import", data={"source": "chesscom", "username": "me", "max": 5}).get_json()
    time.sleep(0.5)
    assert c.get(f"/api/import/{job2['job_id']}").get_json()["skipped"] == 1
