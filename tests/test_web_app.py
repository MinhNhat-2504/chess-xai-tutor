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
