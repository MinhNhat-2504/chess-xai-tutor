"""Web UI: dán hoặc upload PGN, phân tích và giải thích từng nước trên trình duyệt.

Flask server nhỏ chạy local:

* ``GET /`` — trang chính (dán PGN / chọn file, xem phân tích).
* ``POST /api/analyze`` — nhận PGN, tạo job phân tích chạy nền, trả ``job_id``.
* ``GET /api/job/<id>?since=N`` — poll kết quả: các báo cáo mới từ nước N trở đi,
  nên trang web hiện dần từng nước như viewer Pygame thay vì chờ cả ván.
* ``GET /board.svg`` — vẽ bàn cờ bằng SVG có sẵn của python-chess (không cần
  thư viện JS ngoài, trang chạy được offline).

Mỗi job dùng một ``MoveExplainer`` riêng trong thread riêng (engine UCI không
thread-safe) và tự đóng engine khi xong.
"""
from __future__ import annotations

import io
import threading
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any

import chess
import chess.pgn
import chess.svg
from flask import Flask, Response, abort, jsonify, render_template, request

from ..xai import MoveExplainer, format_summary_vi, summarize_game
from ..xai.game_import import ImportError_, fetch_games, player_color
from ..xai.profile import build_profile
from ..xai.store import TutorStore

_MAX_PGN_BYTES = 200_000
_MAX_PLIES = 300
_MAX_JOBS = 20

_jobs: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_jobs_lock = threading.Lock()


def parse_pgn(text: str) -> tuple[chess.pgn.Game, list[chess.Move]]:
    """Đọc ván đầu tiên từ chuỗi PGN; ném ``ValueError`` kèm thông báo tiếng Việt."""
    text = (text or "").strip()
    if not text:
        raise ValueError("PGN trống — hãy dán nội dung PGN hoặc chọn file .pgn.")
    if len(text.encode("utf-8", errors="ignore")) > _MAX_PGN_BYTES:
        raise ValueError("PGN quá lớn (giới hạn 200KB — một ván cờ bình thường chỉ vài KB).")
    game = chess.pgn.read_game(io.StringIO(text))
    if game is None:
        raise ValueError("Không đọc được ván cờ nào từ nội dung đã dán.")
    moves = list(game.mainline_moves())
    if not moves:
        raise ValueError("PGN không chứa nước đi nào — kiểm tra lại nội dung đã dán.")
    return game, moves[:_MAX_PLIES]


def _job_snapshot(job_id: str, since: int) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return {}
        return {
            "status": job["status"],
            "total": job["total"],
            "analyzed": len(job["reports"]),
            "reports": job["reports"][since:],
            "headers": job["headers"],
            "initial_fen": job["initial_fen"],
            "engine": job["engine"],
            "summary_lines": job.get("summary_lines"),
            "summary": job.get("summary"),
            "error_message": job.get("error_message"),
        }


def _run_job(job_id: str, starting_fen: str | None, moves: list[chess.Move], explainer_kwargs: dict) -> None:
    explainer = MoveExplainer(**explainer_kwargs)
    with _jobs_lock:
        _jobs[job_id]["engine"] = explainer.engine_label
    try:
        board = chess.Board(starting_fen) if starting_fen else chess.Board()
        for ply, move in enumerate(moves, start=1):
            report = explainer.analyze_move(board, move)
            report["ply"] = ply
            report["move_number"] = board.fullmove_number
            board.push(move)
            report["fen_after"] = board.fen()
            with _jobs_lock:
                _jobs[job_id]["reports"].append(report)
        with _jobs_lock:
            job = _jobs[job_id]
            job["summary"] = summarize_game(job["reports"])
            job["summary_lines"] = format_summary_vi(job["summary"])
            job["status"] = "done"
    except Exception as exc:
        with _jobs_lock:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error_message"] = str(exc)
    finally:
        explainer.close()


def _analyze_pgn(explainer: MoveExplainer, pgn: str) -> tuple[list[dict], dict]:
    """Phân tích một PGN thành (analysis, summary) — dùng cho nhập hàng loạt."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    moves = list(game.mainline_moves())[:_MAX_PLIES]
    starting_fen = game.headers.get("FEN")
    board = chess.Board(starting_fen) if starting_fen else chess.Board()
    analysis = []
    for ply, move in enumerate(moves, start=1):
        report = explainer.analyze_move(board, move)
        report["ply"] = ply
        report["move_number"] = board.fullmove_number
        board.push(move)
        report["fen_after"] = board.fen()
        analysis.append(report)
    return analysis, summarize_game(analysis)


def _run_import_job(job_id: str, store: TutorStore, source: str, username: str, max_games: int, explainer_kwargs: dict) -> None:
    def update(**fields):
        with _jobs_lock:
            _jobs[job_id].update(fields)

    try:
        games = fetch_games(source, username, max_games)
    except ImportError_ as exc:
        update(status="error", error_message=str(exc))
        return
    except Exception as exc:  # mạng/JSON bất thường
        update(status="error", error_message=f"Không kéo được ván: {exc}")
        return
    playable = [g for g in games if player_color({"White": g.white, "Black": g.black}, username)]
    todo = [g for g in playable if not store.has_analysis(g.id)]
    update(total=len(playable), fetched=len(games), skipped=len(playable) - len(todo), analyzed=0)
    if not playable:
        update(status="done", error_message="Không có ván nào của người chơi này (kiểm tra lại tên).")
        return
    if not todo:
        update(status="done")
        return
    explainer = MoveExplainer(**explainer_kwargs)
    update(engine=explainer.engine_label)
    try:
        for game in todo:
            try:
                analysis, summary = _analyze_pgn(explainer, game.pgn)
                store.save_game(game.to_dict(), username, analysis, summary, explainer.engine_label)
            except Exception as exc:  # một ván hỏng không làm chết cả đợt
                with _jobs_lock:
                    _jobs[job_id].setdefault("failed", []).append(f"{game.id}: {exc}")
            with _jobs_lock:
                _jobs[job_id]["analyzed"] += 1
                _jobs[job_id]["last_game"] = f"{game.white} vs {game.black}"
        update(status="done")
    finally:
        explainer.close()


def create_app(
    use_stockfish: bool = True,
    engine_path: str | None = None,
    engine_depth: int = 14,
    multipv: int = 3,
    fallback_depth: int = 2,
    engine_time_s: float | None = 1.5,
    db_path: str | Path = "data/tutor.db",
) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
    explainer_kwargs = dict(
        depth=fallback_depth,
        use_stockfish=use_stockfish,
        engine_path=engine_path,
        engine_depth=engine_depth,
        multipv=multipv,
        engine_time_s=engine_time_s,
    )
    store = TutorStore(db_path)
    # Một oracle dùng chung (có khoá) để chấm nước người học đi trong bài tập.
    puzzle_lock = threading.Lock()
    puzzle_explainer: dict[str, MoveExplainer | None] = {"obj": None}

    def puzzle_oracle() -> MoveExplainer | None:
        if puzzle_explainer["obj"] is None:
            puzzle_explainer["obj"] = MoveExplainer(**explainer_kwargs)
        return puzzle_explainer["obj"] if puzzle_explainer["obj"].oracle is not None else None

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/analyze")
    def analyze():
        text = request.form.get("pgn", "")
        upload = request.files.get("file")
        depth_override = request.form.get("depth", type=int)
        if upload is not None and not text.strip():
            text = upload.read(_MAX_PGN_BYTES + 1).decode("utf-8-sig", errors="replace")
        try:
            game, moves = parse_pgn(text)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        job_id = uuid.uuid4().hex[:12]
        headers = {
            key: game.headers.get(key, "")
            for key in ("White", "Black", "Result", "Date", "Event", "WhiteElo", "BlackElo")
            if game.headers.get(key)
        }
        with _jobs_lock:
            _jobs[job_id] = {
                "status": "running",
                "total": len(moves),
                "reports": [],
                "headers": headers,
                "initial_fen": game.headers.get("FEN") or chess.STARTING_FEN,
                "engine": "",
            }
            while len(_jobs) > _MAX_JOBS:
                _jobs.popitem(last=False)
        job_kwargs = dict(explainer_kwargs)
        if depth_override:
            job_kwargs["engine_depth"] = max(8, min(20, depth_override))
            if job_kwargs["engine_depth"] >= 16:
                job_kwargs["engine_time_s"] = 3.0  # phân tích kỹ: nới nắp thời gian
        threading.Thread(
            target=_run_job,
            args=(job_id, game.headers.get("FEN"), moves, job_kwargs),
            daemon=True,
        ).start()
        return jsonify({"job_id": job_id, "total": len(moves)})

    @app.get("/api/job/<job_id>")
    def job_status(job_id: str):
        since = max(0, request.args.get("since", default=0, type=int))
        snapshot = _job_snapshot(job_id, since)
        if not snapshot:
            return jsonify({"error": "Không tìm thấy phiên phân tích (server có thể đã khởi động lại)."}), 404
        return jsonify(snapshot)

    # ---------------------------------------------------- nhập ván theo tên
    @app.post("/api/import")
    def import_games():
        source = (request.form.get("source") or "chesscom").strip()
        username = (request.form.get("username") or "").strip()
        max_games = request.form.get("max", default=20, type=int) or 20
        if not username:
            return jsonify({"error": "Hãy nhập tên người chơi."}), 400
        job_id = uuid.uuid4().hex[:12]
        with _jobs_lock:
            _jobs[job_id] = {"kind": "import", "status": "running", "source": source, "username": username,
                             "total": 0, "fetched": 0, "analyzed": 0, "skipped": 0, "engine": "", "failed": []}
            while len(_jobs) > _MAX_JOBS:
                _jobs.popitem(last=False)
        threading.Thread(target=_run_import_job, args=(job_id, store, source, username, max_games, explainer_kwargs), daemon=True).start()
        return jsonify({"job_id": job_id})

    @app.get("/api/import/<job_id>")
    def import_status(job_id: str):
        with _jobs_lock:
            job = _jobs.get(job_id)
            snapshot = dict(job) if job else None
        if not snapshot:
            return jsonify({"error": "Không tìm thấy phiên nhập."}), 404
        return jsonify(snapshot)

    @app.get("/api/games")
    def list_games():
        username = (request.args.get("username") or "").strip()
        if not username:
            return jsonify({"games": [], "users": store.known_users()})
        return jsonify({"games": store.list_games(username), "users": store.known_users()})

    @app.get("/api/games/<path:game_id>")
    def get_game(game_id: str):
        game = store.get_game(game_id)
        if game is None:
            return jsonify({"error": "Không có ván này."}), 404
        return jsonify(game)

    @app.get("/api/profile")
    def profile():
        username = (request.args.get("username") or "").strip()
        if not username:
            return jsonify({"error": "Thiếu tên người chơi."}), 400
        games = [store.get_game(g["id"]) for g in store.list_games(username)]
        return jsonify(build_profile([g for g in games if g]))

    # ------------------------------------------------------------- bài tập
    @app.get("/api/puzzles/next")
    def next_puzzle():
        username = (request.args.get("username") or "").strip()
        if not username:
            return jsonify({"error": "Thiếu tên người chơi."}), 400
        puzzle = store.next_puzzle(username)
        return jsonify({"puzzle": puzzle, "stats": store.puzzle_stats(username)})

    @app.post("/api/puzzles/<int:puzzle_id>/answer")
    def answer_puzzle(puzzle_id: int):
        puzzle = store.get_puzzle(puzzle_id)
        if puzzle is None:
            return jsonify({"error": "Không có bài này."}), 404
        move_uci = (request.form.get("move") or "").strip()
        board = chess.Board(puzzle["fen"])
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            return jsonify({"error": "Nước đi không hợp lệ."}), 400
        if move not in board.legal_moves:
            return jsonify({"error": "Nước đi không hợp lệ."}), 400
        correct = move_uci == puzzle["answer_uci"]
        verdict = "exact" if correct else "wrong"
        alt_note = ""
        if not correct:
            oracle = puzzle_oracle()
            if oracle is not None:
                with puzzle_lock:
                    result = oracle.oracle.analyze(board, move)
                best = result["candidates"][0]["score"] if result["candidates"] else None
                played = result["played"]["score"] if result["played"] else None
                if best is not None and played is not None and best - played <= 30:
                    correct, verdict = True, "alternative"
                    alt_note = f"Cũng được! Nước mạnh nhất là {puzzle['answer_san']}."
        schedule = store.record_answer(puzzle_id, correct)
        return jsonify({"correct": correct, "verdict": verdict, "note": alt_note, "answer_san": puzzle["answer_san"],
                        "answer_uci": puzzle["answer_uci"], "line": puzzle["line"], "schedule": schedule,
                        "stats": store.puzzle_stats(puzzle["username"])})

    @app.get("/board.svg")
    def board_svg():
        try:
            board = chess.Board(request.args.get("fen", chess.STARTING_FEN))
        except ValueError:
            abort(400)
        lastmove = None
        lastmove_arg = request.args.get("lastmove", "")
        if lastmove_arg:
            try:
                lastmove = chess.Move.from_uci(lastmove_arg)
            except ValueError:
                lastmove = None
        size = min(720, max(240, request.args.get("size", default=480, type=int)))
        check_square = board.king(board.turn) if board.is_check() else None
        arrows = []
        for spec in request.args.get("arrows", "").split(","):
            spec = spec.strip()
            if not spec:
                continue
            uci, _, color = spec.partition(":")
            try:
                move = chess.Move.from_uci(uci)
            except ValueError:
                continue
            arrows.append(chess.svg.Arrow(move.from_square, move.to_square, color=color or "#5bc0de99"))
        orientation = chess.BLACK if request.args.get("orientation") == "black" else chess.WHITE
        fill: dict[int, str] = {}
        selected = request.args.get("selected", "")
        if selected:
            try:
                sq = chess.parse_square(selected)
                fill[sq] = "#f6f66999"
                for mv in board.legal_moves:
                    if mv.from_square == sq:
                        fill[mv.to_square] = "#4897605e"
            except ValueError:
                pass
        svg = chess.svg.board(
            board=board, lastmove=lastmove, check=check_square, arrows=arrows,
            size=size, orientation=orientation, fill=fill,
        )
        return Response(svg, mimetype="image/svg+xml")

    return app
