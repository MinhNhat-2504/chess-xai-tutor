"""Hồ sơ điểm yếu cá nhân: gộp nhiều ván đã phân tích của một người chơi.

Khác với tổng kết một ván (``game_summary``), hồ sơ chỉ tính **các nước của
chính người chơi** (theo màu họ cầm trong từng ván) và trả lời:

* độ chính xác trung bình + xu hướng theo thời gian;
* sai ở giai đoạn nào (khai/trung/tàn cuộc) — tỉ lệ lỗi trên mỗi ván;
* hay để hở đòn gì (đòn đôi, ghim...), tính trên số ván;
* khai cuộc nào chơi tệ nhất (theo tên khai cuộc hoặc 3 nước đầu);
* vài ví dụ lỗi lặp lại (nước tệ nhất kèm ván + số nước để nhảy tới).

Đầu ra kèm ``insights_vi`` — 3-5 câu ngắn cho người học đọc ngay.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import chess

from .game_summary import PHASE_LABELS_VI, game_phase, move_accuracy, win_chance_from_cp
from .motifs import MOTIF_LABELS_VI

_ERROR = ("inaccuracy", "mistake", "blunder")


def _opening_key(game: dict[str, Any], analysis: list[dict]) -> str:
    if game.get("opening"):
        return game["opening"]
    sans = [r["move_san"] for r in analysis[:6]]
    return " ".join(sans) if sans else "?"


def build_profile(games: list[dict[str, Any]]) -> dict[str, Any]:
    """``games``: dict từ ``TutorStore.get_game`` (có ``analysis``, ``user_color``)."""
    played = [g for g in games if g.get("user_color") and g.get("analysis")]
    if not played:
        return {"games": 0, "insights_vi": ["Chưa có ván nào được phân tích cho người chơi này."]}

    accuracies: list[dict[str, Any]] = []
    quality_counts: Counter = Counter()
    phase_errors: Counter = Counter()
    phase_moves: Counter = Counter()
    motif_counts: Counter = Counter()
    openings: dict[str, dict[str, Any]] = defaultdict(lambda: {"games": 0, "acc_sum": 0.0, "first_error_ply": []})
    worst: list[dict[str, Any]] = []
    total_moves = 0
    results = Counter()

    for game in sorted(played, key=lambda g: (g.get("date") or "", g.get("analyzed_at") or 0)):
        color = game["user_color"]
        my_reports = [r for r in game["analysis"] if r["side"] == color]
        if not my_reports:
            continue
        accs = [
            move_accuracy(win_chance_from_cp(float(r["best_score"])), win_chance_from_cp(float(r["score"])))
            for r in my_reports
        ]
        game_acc = sum(accs) / len(accs)
        accuracies.append({"game_id": game["id"], "date": game.get("date", ""), "accuracy": round(game_acc, 1),
                           "opponent": game.get("black") if color == "white" else game.get("white"),
                           "result": game.get("result", "*")})
        results[_outcome(game.get("result", "*"), color)] += 1
        total_moves += len(my_reports)
        first_error = None
        for r in my_reports:
            quality_counts[r["quality"]] += 1
            phase = game_phase(chess.Board(r["fen"]))
            phase_moves[phase] += 1
            if r["quality"] in _ERROR:
                phase_errors[phase] += 1
                if first_error is None:
                    first_error = r.get("ply", 0)
            for m in r.get("opponent_motifs") or []:
                motif_counts[m["kind"]] += 1
            if r["quality"] in ("mistake", "blunder"):
                worst.append({
                    "game_id": game["id"], "ply": r.get("ply"), "label": _label(r), "quality": r["quality"],
                    "loss": r.get("centipawn_loss", 0), "headline": r.get("headline_vi", ""),
                    "date": game.get("date", ""), "opponent": accuracies[-1]["opponent"],
                })
        key = _opening_key(game, game["analysis"])
        openings[key]["games"] += 1
        openings[key]["acc_sum"] += game_acc
        if first_error is not None:
            openings[key]["first_error_ply"].append(first_error)

    n_games = len(accuracies)
    avg_acc = sum(a["accuracy"] for a in accuracies) / n_games
    recent = accuracies[-5:]
    older = accuracies[:-5] if len(accuracies) > 5 else []
    trend = None
    if older:
        trend = round(sum(a["accuracy"] for a in recent) / len(recent) - sum(a["accuracy"] for a in older) / len(older), 1)

    phase_rows = []
    for phase, label in PHASE_LABELS_VI.items():
        moves = phase_moves.get(phase, 0)
        errors = phase_errors.get(phase, 0)
        phase_rows.append({
            "phase": phase, "label_vi": label, "moves": moves, "errors": errors,
            "error_rate": round(100 * errors / moves, 1) if moves else 0.0,
            "errors_per_game": round(errors / n_games, 2),
        })
    motif_rows = sorted(
        ({"kind": k, "label_vi": MOTIF_LABELS_VI.get(k, k), "count": c, "per_game": round(c / n_games, 2)} for k, c in motif_counts.items()),
        key=lambda x: -x["count"],
    )
    opening_rows = sorted(
        (
            {"opening": k, "games": v["games"], "accuracy": round(v["acc_sum"] / v["games"], 1),
             "avg_first_error_move": round(sum(v["first_error_ply"]) / len(v["first_error_ply"]) / 2 + 0.5, 1) if v["first_error_ply"] else None}
            for k, v in openings.items()
        ),
        key=lambda x: (x["accuracy"], -x["games"]),
    )
    worst.sort(key=lambda w: -float(w["loss"]))

    profile = {
        "games": n_games,
        "moves": total_moves,
        "accuracy": round(avg_acc, 1),
        "trend": trend,
        "results": {"win": results.get("win", 0), "draw": results.get("draw", 0), "loss": results.get("loss", 0)},
        "accuracy_history": accuracies,
        "quality_counts": {q: quality_counts.get(q, 0) for q in ("best", "good", "inaccuracy", "mistake", "blunder")},
        "phases": phase_rows,
        "motifs": motif_rows,
        "openings": opening_rows[:6],
        "worst_moves": worst[:8],
    }
    profile["insights_vi"] = _insights(profile)
    return profile


def _outcome(result: str, color: str) -> str:
    if result == "1/2-1/2":
        return "draw"
    if result == "1-0":
        return "win" if color == "white" else "loss"
    if result == "0-1":
        return "win" if color == "black" else "loss"
    return "draw"


def _label(report: dict[str, Any]) -> str:
    number = report.get("move_number", 0)
    prefix = f"{number}." if report["side"] == "white" else f"{number}..."
    return prefix + report.get("move_san", "")


def _insights(p: dict[str, Any]) -> list[str]:
    lines = []
    n = p["games"]
    lines.append(f"Độ chính xác trung bình {p['accuracy']:.0f}% trên {n} ván" + (
        f", {'tăng' if p['trend'] > 0 else 'giảm'} {abs(p['trend']):.0f} điểm ở 5 ván gần nhất." if p.get("trend") is not None and abs(p["trend"]) >= 1 else "."
    ))
    phases = [ph for ph in p["phases"] if ph["moves"] >= 5]
    if phases:
        weakest = max(phases, key=lambda ph: ph["error_rate"])
        if weakest["error_rate"] >= 5:
            lines.append(
                f"Yếu nhất ở {weakest['label_vi']}: cứ 100 nước thì sai {weakest['error_rate']:.0f} nước "
                f"(~{weakest['errors_per_game']:.1f} lỗi mỗi ván)."
            )
    if p["motifs"]:
        top = p["motifs"][0]
        if top["count"] >= 2:
            lines.append(f"Đòn hay để hở nhất: {top['label_vi']} — {top['count']} lần trong {n} ván. Hãy luyện bài tập về đòn này.")
    ops = [o for o in p["openings"] if o["games"] >= 2]
    if ops:
        o = ops[0]
        text = f"Khai cuộc chơi tệ nhất: {o['opening']} ({o['games']} ván, chính xác {o['accuracy']:.0f}%)"
        if o.get("avg_first_error_move"):
            text += f", thường sai từ khoảng nước {o['avg_first_error_move']:.0f}"
        lines.append(text + ".")
    qc = p["quality_counts"]
    if qc.get("blunder", 0):
        lines.append(f"Trung bình {qc['blunder'] / n:.1f} sai lầm nghiêm trọng mỗi ván — giảm được con số này là lên trình nhanh nhất.")
    return lines
