"""Tổng kết ván đấu từ các báo cáo XAI theo từng nước.

Trả lời câu hỏi của người học sau một ván: *tôi chơi chính xác bao nhiêu, sai
ở giai đoạn nào, nước nào tệ nhất, và tôi hay để hở đòn gì?*

* **Accuracy** mỗi nước quy đổi từ mức sụt "cơ hội thắng" theo công thức
  Lichess; accuracy ván = trung bình các nước. Hoạt động với cả điểm Stockfish
  lẫn evaluator nội bộ vì chỉ cần ``score``/``best_score`` centipawn.
* **ACPL** — average centipawn loss, chỉ số chuẩn khi so trình độ.
* **Lỗi theo giai đoạn** khai cuộc / trung cuộc / tàn cuộc: giai đoạn xác định
  bằng vật chất còn lại (không tính tốt/vua) và số nước đã đi.
* **Motif bị bỏ hở**: đếm các motif đối thủ được phép tạo (``opponent_motifs``)
  — gợi ý chủ đề chiến thuật cần luyện.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable

import chess

from ..evaluation.piece_tables import PIECE_VALUES
from .motifs import MOTIF_LABELS_VI


_ERROR_QUALITIES = ("inaccuracy", "mistake", "blunder")

PHASE_LABELS_VI = {
    "opening": "khai cuộc",
    "middlegame": "trung cuộc",
    "endgame": "tàn cuộc",
}
QUALITY_LABELS_VI = {
    "best": "nước tốt nhất",
    "good": "nước tốt",
    "inaccuracy": "thiếu chính xác",
    "mistake": "sai lầm",
    "blunder": "blunder",
}

# Tổng giá trị mã/tượng/xe/hậu hai bên còn lại từ mức này trở xuống là tàn cuộc
# (tương đương mỗi bên còn ~1 xe + 1 quân nhẹ).
_ENDGAME_MATERIAL = 1700
_OPENING_FULLMOVES = 10


def win_chance_from_cp(cp: float) -> float:
    """Xác suất thắng ước lượng theo công thức Lichess, tính từ centipawn."""
    return round(50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1), 1)


def move_accuracy(win_before: float, win_after: float) -> float:
    """Accuracy một nước (0-100) từ mức sụt cơ hội thắng, theo Lichess."""
    drop = max(0.0, win_before - win_after)
    raw = 103.1668 * math.exp(-0.04354 * drop) - 3.1669
    return max(0.0, min(100.0, raw))


def game_phase(board: chess.Board) -> str:
    """Phân loại khai cuộc / trung cuộc / tàn cuộc cho một thế cờ."""
    material = sum(
        PIECE_VALUES[piece.piece_type]
        for piece in board.piece_map().values()
        if piece.piece_type not in (chess.PAWN, chess.KING)
    )
    if material <= _ENDGAME_MATERIAL:
        return "endgame"
    if board.fullmove_number <= _OPENING_FULLMOVES:
        return "opening"
    return "middlegame"


def summarize_game(reports: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Gộp các báo cáo ``MoveExplainer.analyze_move`` thành tổng kết một ván."""
    sides: dict[str, dict[str, Any]] = {
        side: {
            "moves": 0,
            "losses": [],
            "accuracies": [],
            "counts": Counter(),
            "allowed_motifs": Counter(),
        }
        for side in ("white", "black")
    }
    phase_errors = {phase: {"white": 0, "black": 0} for phase in PHASE_LABELS_VI}
    worst: list[dict[str, Any]] = []

    for report in reports:
        side = report["side"]
        data = sides[side]
        loss = float(report["centipawn_loss"])
        board = chess.Board(report["fen"])
        phase = game_phase(board)

        data["moves"] += 1
        data["losses"].append(loss)
        data["accuracies"].append(move_accuracy(
            win_chance_from_cp(float(report["best_score"])),
            win_chance_from_cp(float(report["score"])),
        ))
        data["counts"][report["quality"]] += 1
        for motif in report.get("opponent_motifs", []):
            data["allowed_motifs"][motif["kind"]] += 1

        if report["quality"] in _ERROR_QUALITIES:
            phase_errors[phase][side] += 1
            prefix = f"{board.fullmove_number}." if side == "white" else f"{board.fullmove_number}..."
            worst.append({
                "label": f"{prefix}{report['move_san']}",
                "side": side,
                "quality": report["quality"],
                "quality_vi": QUALITY_LABELS_VI.get(report["quality"], report["quality"]),
                "centipawn_loss": loss,
                "ply": report.get("ply"),
                "phase": phase,
            })

    summary: dict[str, Any] = {"phase_errors": phase_errors}
    for side, data in sides.items():
        losses, accuracies = data["losses"], data["accuracies"]
        summary[side] = {
            "moves": data["moves"],
            "acpl": round(sum(losses) / len(losses), 1) if losses else 0.0,
            "accuracy": round(sum(accuracies) / len(accuracies), 1) if accuracies else 0.0,
            "counts": {q: data["counts"].get(q, 0) for q in QUALITY_LABELS_VI},
            "allowed_motifs": dict(data["allowed_motifs"]),
        }
    summary["worst_moves"] = sorted(worst, key=lambda item: item["centipawn_loss"], reverse=True)[:5]
    return summary


def format_summary_vi(summary: dict[str, Any]) -> list[str]:
    """Diễn giải tổng kết thành các dòng tiếng Việt ngắn cho UI."""
    lines: list[str] = []
    side_names = {"white": "Trắng", "black": "Đen"}
    for side in ("white", "black"):
        data = summary[side]
        if not data["moves"]:
            continue
        counts = data["counts"]
        error_text = ", ".join(
            f"{counts[q]} {QUALITY_LABELS_VI[q]}"
            for q in _ERROR_QUALITIES
            if counts.get(q)
        ) or "không có lỗi đáng kể"
        lines.append(
            f"{side_names[side]}: accuracy {data['accuracy']:.1f}% | ACPL {data['acpl']:.0f} | {error_text}"
        )

    phase_parts = []
    for phase, label in PHASE_LABELS_VI.items():
        errors = summary["phase_errors"][phase]
        if errors["white"] or errors["black"]:
            phase_parts.append(f"{label}: Trắng {errors['white']} / Đen {errors['black']}")
    if phase_parts:
        lines.append("Lỗi theo giai đoạn — " + "; ".join(phase_parts))

    if summary["worst_moves"]:
        worst_text = ", ".join(
            f"{item['label']} ({item['quality_vi']}, -{item['centipawn_loss']:.0f})"
            for item in summary["worst_moves"][:3]
        )
        lines.append(f"Nước cần xem lại: {worst_text}")

    motif_parts = []
    for side in ("white", "black"):
        for kind, count in summary[side]["allowed_motifs"].items():
            label = MOTIF_LABELS_VI.get(kind, kind)
            motif_parts.append(f"{side_names[side]} để hở {label} ×{count}")
    if motif_parts:
        lines.append("Chủ đề cần luyện: " + "; ".join(motif_parts))

    return lines
