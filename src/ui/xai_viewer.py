"""Pygame viewer để học cờ từ file PGN của Chess.com hoặc Lichess.

Pygame chỉ được import trong :func:`run_xai_viewer`, vì vậy các helper đọc PGN
vẫn test được trên máy không cài giao diện đồ hoạ.
"""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Any

import chess
import chess.pgn

from ..xai import MoveExplainer, format_summary_vi, summarize_game
from .pygame_app import (
    ACCENT, BG, DARK, LAST_MOVE, LIGHT, MUTED, PANEL, PANEL_HOVER, TEXT,
    _draw_piece, _square_to_xy,
)


_ERROR_QUALITIES = {"inaccuracy", "mistake", "blunder"}
_QUALITY_COLORS = {
    "best": (90, 190, 122),
    "good": (91, 192, 222),
    "inaccuracy": (235, 186, 73),
    "mistake": (237, 126, 67),
    "blunder": (223, 79, 79),
}


def read_pgn(path: str | Path) -> chess.pgn.Game:
    """Đọc ván đầu tiên từ PGN xuất bởi Chess.com/Lichess."""
    path = Path(path)
    if path.suffix.lower() != ".pgn":
        raise ValueError("Chỉ hỗ trợ file .pgn từ Chess.com hoặc Lichess.")
    with path.open(encoding="utf-8-sig", errors="replace") as handle:
        game = chess.pgn.read_game(handle)
    if game is None:
        raise ValueError("Không tìm thấy ván cờ hợp lệ trong file PGN.")
    return game


def game_positions(game: chess.pgn.Game) -> tuple[chess.Board, list[chess.Move], list[chess.Board]]:
    """Trả bàn đầu, danh sách nước chính và các trạng thái sau từng nước."""
    starting_fen = game.headers.get("FEN")
    initial = chess.Board(starting_fen) if starting_fen else chess.Board()
    moves = list(game.mainline_moves())
    board = initial.copy(stack=False)
    positions = [board.copy(stack=False)]
    for move in moves:
        board.push(move)
        positions.append(board.copy(stack=False))
    return initial, moves, positions


def next_error_index(reports: dict[int, dict[str, Any]], current: int, total: int) -> int | None:
    """Tìm nửa-nước lỗi kế tiếp; ``current`` là số nước đang hiển thị."""
    for index in range(current, total):
        if reports.get(index, {}).get("quality") in _ERROR_QUALITIES:
            return index + 1  # vị trí bàn sau khi nước index đã được đi
    return None


def _pick_pgn_file() -> str | None:
    """Mở native file dialog khi tkinter có sẵn; drag-and-drop vẫn luôn dùng được."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(
            title="Chọn PGN từ Chess.com hoặc Lichess",
            filetypes=[("PGN chess game", "*.pgn"), ("All files", "*.*")],
        )
        root.destroy()
        return selected or None
    except Exception:
        return None


def _wrap(font, text: str, max_width: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = word if not line else f"{line} {word}"
        if line and font.size(candidate)[0] > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def run_xai_viewer(
    depth: int = 2,
    square_size: int = 64,
    use_stockfish: bool = True,
    engine_path=None,
    engine_depth: int = 12,
) -> None:
    """Mở ứng dụng: chọn/thả PGN, sau đó duyệt và học từ các lỗi."""
    import pygame

    pygame.init()
    pygame.display.set_caption("Chess XAI — Phân tích PGN để học cờ")
    board_px = 8 * square_size
    width, height = max(1100, board_px + 600), max(690, board_px + 150)
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("dejavusans", 24, bold=True)
    header_font = pygame.font.SysFont("dejavusans", 18, bold=True)
    font = pygame.font.SysFont("dejavusans", 15)
    small_font = pygame.font.SysFont("dejavusans", 13)

    game = None
    file_path: Path | None = None
    moves: list[chess.Move] = []
    positions: list[chess.Board] = [chess.Board()]
    reports: dict[int, dict[str, Any]] = {}
    position = 0
    status = "Chọn hoặc kéo-thả file .pgn vào cửa sổ."
    progress = ""
    engine_label = ""
    show_summary = False
    summary_cache: tuple[int, list[str]] = (0, [])
    worker_messages: queue.Queue = queue.Queue()
    session = 0

    def load_game(path_text: str) -> None:
        nonlocal game, file_path, moves, positions, reports, position, status, progress, session
        nonlocal show_summary, summary_cache
        try:
            loaded = read_pgn(path_text)
            _, loaded_moves, loaded_positions = game_positions(loaded)
        except Exception as exc:
            status = f"Không thể đọc file: {exc}"
            return
        if not loaded_moves:
            status = "PGN không có nước đi để phân tích."
            return
        game, file_path, moves, positions = loaded, Path(path_text), loaded_moves, loaded_positions
        reports, position = {}, 0
        show_summary, summary_cache = False, (0, [])
        session += 1
        active_session = session
        status = f"Đã tải {file_path.name}. Đang phân tích..."
        progress = f"0/{len(moves)} nước"

        def analyze_in_background() -> None:
            # Mỗi lượt tải file dùng một explainer (một tiến trình engine) riêng
            # vì SimpleEngine không dùng chung giữa các thread được.
            explainer = MoveExplainer(
                depth=depth,
                use_stockfish=use_stockfish,
                engine_path=engine_path,
                engine_depth=engine_depth,
            )
            worker_messages.put((active_session, "engine", None, explainer.engine_label))
            try:
                for index, move in enumerate(moves):
                    report = explainer.analyze_move(positions[index], move)
                    worker_messages.put((active_session, "report", index, report))
                worker_messages.put((active_session, "done", None, None))
            except Exception as exc:  # hiển thị lỗi thay vì để thread chết im lặng
                worker_messages.put((active_session, "error", None, str(exc)))
            finally:
                explainer.close()

        threading.Thread(target=analyze_in_background, daemon=True).start()

    def button(rect, label, mouse_pos, enabled=True):
        color = PANEL_HOVER if enabled and rect.collidepoint(mouse_pos) else PANEL
        if not enabled:
            color = (47, 50, 57)
        pygame.draw.rect(screen, color, rect, border_radius=7)
        pygame.draw.rect(screen, ACCENT if enabled else MUTED, rect, width=1, border_radius=7)
        text = small_font.render(label, True, TEXT if enabled else MUTED)
        screen.blit(text, text.get_rect(center=rect.center))

    running = True
    while running:
        while True:
            try:
                message_session, kind, index, payload = worker_messages.get_nowait()
            except queue.Empty:
                break
            if message_session != session:
                continue  # kết quả từ file cũ được bỏ qua
            if kind == "report":
                reports[index] = payload
                progress = f"{len(reports)}/{len(moves)} nước"
            elif kind == "engine":
                engine_label = payload
            elif kind == "done":
                status = f"Đã phân tích {len(moves)} nước. Dùng nút 'Lỗi kế' để học nhanh."
            elif kind == "error":
                status = f"Dừng phân tích: {payload}"

        mouse_pos = pygame.mouse.get_pos()
        screen.fill(BG)
        panel_x = board_px + 16
        panel_w = width - panel_x - 16
        load_rect = pygame.Rect(panel_x, 72, 150, 38)
        prev_rect = pygame.Rect(panel_x + 158, 72, 58, 38)
        next_rect = pygame.Rect(panel_x + 224, 72, 58, 38)
        error_rect = pygame.Rect(panel_x + 290, 72, 100, 38)
        summary_rect = pygame.Rect(panel_x + 398, 72, 100, 38)

        # Bàn cờ tại vị trí sau `position` nước đi.
        board = positions[position]
        last_move = moves[position - 1] if position else None
        for square in chess.SQUARES:
            x, y = _square_to_xy(square, square_size, chess.WHITE)
            light = (chess.square_file(square) + chess.square_rank(square)) % 2 == 1
            color = LIGHT if light else DARK
            if last_move and square in (last_move.from_square, last_move.to_square):
                color = LAST_MOVE
            pygame.draw.rect(screen, color, (x, y, square_size, square_size))
            piece = board.piece_at(square)
            if piece:
                _draw_piece(pygame, screen, piece, x, y, square_size)

        pygame.draw.rect(screen, PANEL, (panel_x - 8, 12, panel_w + 8, height - 24), border_radius=10)
        title = title_font.render("Phân tích XAI từ lịch sử ván cờ", True, TEXT)
        screen.blit(title, (panel_x, 24))
        subtitle = small_font.render("PGN Chess.com / Lichess · kéo-thả file hoặc bấm chọn file", True, MUTED)
        screen.blit(subtitle, (panel_x, 51))
        button(load_rect, "Chọn file PGN", mouse_pos)
        button(prev_rect, "← Trước", mouse_pos, position > 0)
        button(next_rect, "Sau →", mouse_pos, position < len(moves))
        button(error_rect, "Lỗi kế", mouse_pos, bool(reports))
        button(summary_rect, "Tổng kết", mouse_pos, bool(reports))

        file_label = file_path.name if file_path else "Chưa có file PGN"
        screen.blit(small_font.render(f"File: {file_label}", True, TEXT), (panel_x, 122))
        engine_text = engine_label or f"Alpha-Beta depth={depth}"
        screen.blit(small_font.render(f"Phân tích: {progress or '-'}  |  {engine_text}", True, MUTED), (panel_x, 142))
        screen.blit(small_font.render(status, True, MUTED), (panel_x, height - 31))

        report = reports.get(position - 1) if position else None
        content_y = 178
        if show_summary and reports:
            if summary_cache[0] != len(reports):
                summary = summarize_game([reports[key] for key in sorted(reports)])
                summary_cache = (len(reports), format_summary_vi(summary))
            screen.blit(header_font.render("Tổng kết ván", True, ACCENT), (panel_x, content_y))
            y = content_y + 32
            for line in summary_cache[1]:
                for text_line in _wrap(font, line, panel_w - 16)[:4]:
                    screen.blit(font.render(text_line, True, TEXT), (panel_x, y))
                    y += 21
                y += 7
            if len(reports) < len(moves):
                note = f"(mới phân tích {len(reports)}/{len(moves)} nước — tổng kết sẽ đầy đủ khi xong)"
                screen.blit(small_font.render(note, True, MUTED), (panel_x, y))
        elif report:
            quality = report["quality"]
            quality_color = _QUALITY_COLORS.get(quality, TEXT)
            heading = header_font.render(
                f"{position}. {report['move_san']} — {report['quality_vi'].upper()}", True, quality_color
            )
            screen.blit(heading, (panel_x, content_y))
            screen.blit(font.render(
                f"Thiệt hại: {report['centipawn_loss']:.0f} | Nước tốt hơn: {report['best_move_san']}", True, TEXT
            ), (panel_x, content_y + 29))
            y = content_y + 61
            if "win_chance" in report:
                win_line = f"Cơ hội thắng sau nước này: {report['win_chance']:.0f}% (nước tốt nhất: {report['win_chance_best']:.0f}%)"
                screen.blit(font.render(win_line, True, TEXT), (panel_x, y))
                y += 24
            if quality in _ERROR_QUALITIES and report.get("refutation_san"):
                for line in _wrap(font, f"Trừng phạt: {report['refutation_san']}", panel_w - 16)[:2]:
                    screen.blit(font.render(line, True, _QUALITY_COLORS["mistake"]), (panel_x, y))
                    y += 21
                y += 3
            for item in report.get("reasons", [])[:3]:
                sign = "+" if item["delta"] >= 0 else ""
                line = f"• {item['label_vi']}: {sign}{item['delta']:.0f}"
                screen.blit(font.render(line, True, TEXT), (panel_x, y))
                y += 21
            for fact in report.get("tactical_facts", [])[:3]:
                for line in _wrap(font, f"• {fact}", panel_w - 16)[:2]:
                    screen.blit(font.render(line, True, TEXT), (panel_x, y))
                    y += 21
            y += 8
            for line in _wrap(font, report["explanation_vi"], panel_w - 16)[:5]:
                screen.blit(font.render(line, True, TEXT), (panel_x, y))
                y += 20
            y += 5
            screen.blit(header_font.render("Top phương án", True, ACCENT), (panel_x, y))
            y += 25
            for item in report["top_candidates"]:
                line = f"{item['move_san']}: {item['score']:+.0f}"
                if item.get("line_san"):
                    line += f"   {item['line_san']}"
                text_lines = _wrap(small_font, line, panel_w - 16)[:1]
                for text_line in text_lines:
                    screen.blit(small_font.render(text_line, True, TEXT), (panel_x, y))
                    y += 19
        elif moves:
            message = "Đang chờ phân tích nước này..." if position else "Bấm 'Sau' để duyệt ván cờ."
            screen.blit(header_font.render(message, True, MUTED), (panel_x, content_y))
        else:
            screen.blit(header_font.render("Thả một file .pgn vào đây để bắt đầu", True, ACCENT), (panel_x, content_y))

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT and position > 0:
                    position -= 1
                elif event.key == pygame.K_RIGHT and position < len(moves):
                    position += 1
                elif event.key in (pygame.K_n, pygame.K_SPACE):
                    found = next_error_index(reports, position, len(moves))
                    if found is not None:
                        position = found
                elif event.key == pygame.K_t and reports:
                    show_summary = not show_summary
            elif event.type == getattr(pygame, "DROPFILE", -1):
                load_game(event.file)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if load_rect.collidepoint(event.pos):
                    selected = _pick_pgn_file()
                    if selected:
                        load_game(selected)
                    else:
                        status = "Không chọn được file. Bạn có thể kéo-thả file .pgn vào cửa sổ."
                elif prev_rect.collidepoint(event.pos) and position > 0:
                    position -= 1
                elif next_rect.collidepoint(event.pos) and position < len(moves):
                    position += 1
                elif error_rect.collidepoint(event.pos):
                    found = next_error_index(reports, position, len(moves))
                    if found is None:
                        status = "Chưa có lỗi tiếp theo; hãy đợi phân tích hoàn tất."
                    else:
                        position = found
                elif summary_rect.collidepoint(event.pos) and reports:
                    show_summary = not show_summary
        clock.tick(30)

    pygame.quit()
