"""Test PGN export + ELO — Báo cáo mục 4.4.4, 4.5."""
import io
import chess
import chess.pgn

from src.analytics.pgn_writer import game_to_pgn, append_pgn_file
from src.analytics.elo import update_elo, expected_score, compute_ratings


# ---------- ELO ----------

def test_expected_score_symmetry():
    assert abs(expected_score(1500, 1500) - 0.5) < 1e-9
    assert expected_score(1700, 1500) > 0.5
    assert expected_score(1300, 1500) < 0.5


def test_update_elo_win_increases_winner():
    new_a, new_b = update_elo(1500, 1500, score_a=1.0, k=32)
    assert new_a > 1500
    assert new_b < 1500
    assert abs((new_a - 1500) + (new_b - 1500)) < 1e-9  # tổng đại số ≈ 0


def test_compute_ratings_winning_agent_climbs():
    """Agent thắng 100 ván liên tiếp sẽ leo ELO rõ rệt."""
    rows = [
        {"white": "winner", "black": "loser", "winner": "winner"}
        for _ in range(100)
    ]
    ratings = compute_ratings(rows, initial=1500.0, k=32.0)
    assert ratings["winner"] > 1700
    assert ratings["loser"] < 1300


def test_compute_ratings_draw_keeps_close():
    rows = [{"white": "a", "black": "b", "winner": "draw"} for _ in range(50)]
    ratings = compute_ratings(rows, initial=1500.0, k=32.0)
    assert abs(ratings["a"] - 1500) < 1.0
    assert abs(ratings["b"] - 1500) < 1.0


# ---------- PGN ----------

def test_pgn_round_trip():
    """PGN xuất ra phải parse được lại qua chess.pgn.read_game."""
    moves = [
        chess.Move.from_uci("e2e4"),
        chess.Move.from_uci("e7e5"),
        chess.Move.from_uci("g1f3"),
    ]
    pgn = game_to_pgn(moves, "white-agent", "black-agent", "*", headers_extra={"Round": "1"})

    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    assert game.headers["White"] == "white-agent"
    assert game.headers["Black"] == "black-agent"
    assert game.headers["Round"] == "1"

    played = [m for m in game.mainline_moves()]
    assert [m.uci() for m in played] == ["e2e4", "e7e5", "g1f3"]


def test_pgn_append_creates_file(tmp_path):
    pgn = game_to_pgn(
        [chess.Move.from_uci("e2e4")], "A", "B", "*",
    )
    path = tmp_path / "games.pgn"
    append_pgn_file(path, pgn)
    append_pgn_file(path, pgn)
    text = path.read_text(encoding="utf-8")
    assert text.count('[White "A"]') == 2


def test_pgn_round_trip_from_custom_fen():
    fen = "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 3"
    move = chess.Move.from_uci("g8f6")
    pgn = game_to_pgn([move], "A", "B", "*", starting_fen=fen)

    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    assert game.headers["SetUp"] == "1"
    assert game.headers["FEN"] == fen
    assert [m.uci() for m in game.mainline_moves()] == ["g8f6"]
