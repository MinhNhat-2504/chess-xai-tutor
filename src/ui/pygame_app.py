"""Pygame GUI cho mô hình AI cờ vua — Báo cáo mục 3.9.

- Bàn cờ 8x8 ô (sáng/tối xen kẽ).
- Quân cờ vẽ bằng shape gần với quân thật, không dùng chữ K/Q/R/B/N/P.
- Màn hình mở đầu cho người chơi chọn độ khó.
- Tương tác: click-click (chọn ô nguồn, click ô đích để di chuyển).
- Animation di chuyển quân và âm thanh chọn / đặt quân / ăn quân.
- Gợi ý nước đi: nhấn H khi đến lượt người chơi.
- Phong cấp: tự động phong thành hậu (đơn giản hoá cho demo).
- Thanh status hiển thị: lượt đi, kết quả ván, nước AI gần nhất, độ sâu / số
  node / thời gian (lấy từ `agent.last_stats`).
- Khi truyền `explainer` (MoveExplainer): mỗi nước đi được phân tích ngầm trong
  một worker thread duy nhất (engine UCI không thread-safe) và câu giải thích
  tiếng Việt hiện dưới bàn cờ; H = gợi ý kèm biến chính; T = tổng kết ván
  (accuracy, ACPL, lỗi theo giai đoạn).

Import `pygame` được đặt BÊN TRONG `run_gui` để các test không cần pygame.
"""
from __future__ import annotations

import array
import math
import queue
import threading
import time
from typing import Optional

import chess

from ..board.chess_env import ChessEnv
from ..xai.game_summary import format_summary_vi, summarize_game


LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
HIGHLIGHT = (246, 246, 105)
LAST_MOVE = (205, 210, 106)
LEGAL_DOT = (72, 151, 92)
HINT_FROM = (80, 150, 235)
HINT_TO = (91, 192, 222)
PIECE_WHITE = (245, 245, 238)
PIECE_BLACK = (38, 41, 47)
PIECE_EDGE = (18, 20, 24)
PIECE_WHITE_SHADE = (214, 205, 184)
PIECE_BLACK_SHADE = (15, 17, 22)
PIECE_GOLD = (212, 175, 91)
BG = (40, 44, 52)
TEXT = (220, 220, 220)
MUTED = (168, 174, 184)
PANEL = (52, 58, 69)
PANEL_HOVER = (68, 77, 91)
ACCENT = (91, 192, 222)


def _difficulty_button_rects(width: int, height: int, count: int):
    button_w = min(440, width - 64)
    button_h = 72
    gap = 16
    total_h = count * button_h + (count - 1) * gap
    start_y = max(128, (height - total_h) // 2 + 22)
    x = (width - button_w) // 2
    return [(x, start_y + i * (button_h + gap), button_w, button_h) for i in range(count)]


def select_difficulty_menu(labels: dict[str, str], default: str = "medium", square_size: int = 64) -> str | None:
    """Hiển thị màn hình chọn độ khó, trả về key difficulty hoặc None nếu đóng."""
    import pygame
    pygame.init()
    pygame.display.set_caption("Chess AI Self-play - Chọn chế độ")

    choices = [key for key in ("easy", "medium", "hell") if key in labels]
    if not choices:
        return default

    width = max(560, 8 * square_size)
    height = 430
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("dejavusans", 30, bold=True)
    label_font = pygame.font.SysFont("dejavusans", 20, bold=True)
    small_font = pygame.font.SysFont("dejavusans", 13)
    selected = choices.index(default) if default in choices else 0

    subtitles = {
        "easy": "Người mới cũng có thể thắng",
        "medium": "Alpha-Beta suy luận nhiều nhánh hơn",
        "hell": "Hybrid + Quantized Q + MCTS",
    }

    while True:
        rects = _difficulty_button_rects(width, height, len(choices))
        mouse_pos = pygame.mouse.get_pos()

        screen.fill(BG)
        title = title_font.render("Chọn Chế Độ", True, TEXT)
        screen.blit(title, title.get_rect(center=(width // 2, 56)))
        note = small_font.render("Bấm Enter hoặc click để bắt đầu", True, MUTED)
        screen.blit(note, note.get_rect(center=(width // 2, 92)))

        for i, key in enumerate(choices):
            rect = pygame.Rect(rects[i])
            is_hover = rect.collidepoint(mouse_pos)
            is_selected = i == selected
            color = PANEL_HOVER if is_hover or is_selected else PANEL
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, ACCENT if is_selected else (78, 86, 99), rect, width=2, border_radius=8)

            marker = small_font.render(str(i + 1), True, ACCENT if is_selected else MUTED)
            screen.blit(marker, (rect.x + 18, rect.y + 14))

            label = label_font.render(labels[key], True, TEXT)
            screen.blit(label, (rect.x + 52, rect.y + 12))
            subtitle = small_font.render(subtitles.get(key, ""), True, MUTED)
            screen.blit(subtitle, (rect.x + 52, rect.y + 43))

        pygame.display.flip()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return None
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return None
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return choices[selected]
                if ev.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(choices)
                elif ev.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(choices)
                elif pygame.K_1 <= ev.key <= pygame.K_9:
                    idx = ev.key - pygame.K_1
                    if idx < len(choices):
                        return choices[idx]
            elif ev.type == pygame.MOUSEMOTION:
                for i, rect in enumerate(rects):
                    if pygame.Rect(rect).collidepoint(ev.pos):
                        selected = i
                        break
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, rect in enumerate(rects):
                    if pygame.Rect(rect).collidepoint(ev.pos):
                        return choices[i]

        clock.tick(60)


def _square_to_xy(sq: int, square_size: int, human_color: bool):
    """Trả (x, y) pixel của góc trên-trái ô `sq`.
    Khi `human_color`=WHITE bàn cờ hiển thị bình thường; ngược lại flip."""
    file = chess.square_file(sq)
    rank = chess.square_rank(sq)
    if human_color == chess.WHITE:
        x = file * square_size
        y = (7 - rank) * square_size
    else:
        x = (7 - file) * square_size
        y = rank * square_size
    return x, y


def _xy_to_square(x: int, y: int, square_size: int, human_color: bool) -> Optional[int]:
    if x < 0 or y < 0 or x >= 8 * square_size or y >= 8 * square_size:
        return None
    file_idx = x // square_size
    rank_idx = y // square_size
    if human_color == chess.WHITE:
        file = file_idx
        rank = 7 - rank_idx
    else:
        file = 7 - file_idx
        rank = rank_idx
    return chess.square(file, rank)


def _candidate_move(board: chess.Board, from_square: int, to_square: int) -> chess.Move:
    move = chess.Move(from_square, to_square)
    piece = board.piece_at(from_square)
    if piece and piece.piece_type == chess.PAWN:
        rank_to = chess.square_rank(to_square)
        if rank_to == 7 or rank_to == 0:
            move = chess.Move(from_square, to_square, promotion=chess.QUEEN)
    return move


def _legal_targets(board: chess.Board, from_square: Optional[int]) -> set[int]:
    if from_square is None:
        return set()
    return {move.to_square for move in board.legal_moves if move.from_square == from_square}


def _draw_piece(pygame, screen, piece: chess.Piece, x: float, y: float, square_size: int) -> None:
    x = int(round(x))
    y = int(round(y))
    s = square_size
    fill = PIECE_WHITE if piece.color == chess.WHITE else PIECE_BLACK
    shade = PIECE_WHITE_SHADE if piece.color == chess.WHITE else PIECE_BLACK_SHADE
    edge = PIECE_EDGE

    def px(rx, ry):
        return (int(x + rx * s), int(y + ry * s))

    def ellipse(rect, color, width=0):
        pygame.draw.ellipse(screen, color, _rect(x, y, s, rect), width)

    def rect(rect, color, width=0, radius=0):
        pygame.draw.rect(screen, color, _rect(x, y, s, rect), width=width, border_radius=radius)

    _draw_piece_base(pygame, screen, x, y, s, fill, shade, edge)

    if piece.piece_type == chess.PAWN:
        pygame.draw.polygon(screen, edge, [px(0.36, 0.64), px(0.64, 0.64), px(0.58, 0.34), px(0.42, 0.34)])
        pygame.draw.polygon(screen, fill, [px(0.39, 0.63), px(0.61, 0.63), px(0.56, 0.38), px(0.44, 0.38)])
        ellipse((0.37, 0.20, 0.26, 0.26), edge)
        ellipse((0.40, 0.23, 0.20, 0.20), fill)
    elif piece.piece_type == chess.KNIGHT:
        pygame.draw.polygon(
            screen,
            edge,
            [px(0.34, 0.64), px(0.62, 0.64), px(0.64, 0.53), px(0.55, 0.43),
             px(0.69, 0.34), px(0.60, 0.19), px(0.43, 0.16), px(0.34, 0.31),
             px(0.43, 0.42)],
        )
        pygame.draw.polygon(
            screen,
            fill,
            [px(0.38, 0.61), px(0.59, 0.61), px(0.59, 0.53), px(0.50, 0.43),
             px(0.62, 0.35), px(0.56, 0.24), px(0.45, 0.22), px(0.39, 0.33),
             px(0.47, 0.42)],
        )
        pygame.draw.circle(screen, shade, px(0.53, 0.29), max(2, s // 35))
        pygame.draw.line(screen, shade, px(0.43, 0.25), px(0.41, 0.52), max(2, s // 24))
    elif piece.piece_type == chess.BISHOP:
        ellipse((0.34, 0.18, 0.32, 0.46), edge)
        ellipse((0.38, 0.22, 0.24, 0.38), fill)
        pygame.draw.line(screen, shade, px(0.58, 0.25), px(0.43, 0.49), max(2, s // 20))
        pygame.draw.circle(screen, edge, px(0.50, 0.17), max(3, s // 18))
        pygame.draw.circle(screen, fill, px(0.50, 0.17), max(2, s // 28))
    elif piece.piece_type == chess.ROOK:
        rect((0.30, 0.24, 0.40, 0.13), edge)
        for rx in (0.31, 0.45, 0.59):
            rect((rx, 0.16, 0.10, 0.12), edge)
            rect((rx + 0.02, 0.18, 0.06, 0.08), fill)
        rect((0.34, 0.28, 0.32, 0.35), fill)
        rect((0.31, 0.58, 0.38, 0.08), edge)
        rect((0.34, 0.59, 0.32, 0.04), fill)
    elif piece.piece_type == chess.QUEEN:
        points = [px(0.25, 0.44), px(0.35, 0.18), px(0.45, 0.41), px(0.50, 0.15),
                  px(0.55, 0.41), px(0.65, 0.18), px(0.75, 0.44), px(0.66, 0.62), px(0.34, 0.62)]
        pygame.draw.polygon(screen, edge, points)
        inner = [px(0.31, 0.44), px(0.37, 0.25), px(0.46, 0.47), px(0.50, 0.23),
                 px(0.54, 0.47), px(0.63, 0.25), px(0.69, 0.44), px(0.62, 0.58), px(0.38, 0.58)]
        pygame.draw.polygon(screen, fill, inner)
        for rx in (0.35, 0.50, 0.65):
            pygame.draw.circle(screen, PIECE_GOLD, px(rx, 0.18 if rx != 0.50 else 0.15), max(3, s // 20))
    elif piece.piece_type == chess.KING:
        rect((0.42, 0.18, 0.16, 0.44), edge, radius=max(2, s // 20))
        rect((0.45, 0.22, 0.10, 0.38), fill, radius=max(2, s // 24))
        pygame.draw.line(screen, edge, px(0.50, 0.10), px(0.50, 0.29), max(2, s // 16))
        pygame.draw.line(screen, edge, px(0.41, 0.18), px(0.59, 0.18), max(2, s // 16))
        pygame.draw.line(screen, PIECE_GOLD, px(0.50, 0.11), px(0.50, 0.27), max(1, s // 28))
        pygame.draw.line(screen, PIECE_GOLD, px(0.43, 0.18), px(0.57, 0.18), max(1, s // 28))


def _rect(x: int, y: int, s: int, rel_rect):
    rx, ry, rw, rh = rel_rect
    return (int(x + rx * s), int(y + ry * s), int(rw * s), int(rh * s))


def _draw_piece_base(pygame, screen, x: int, y: int, s: int, fill, shade, edge) -> None:
    pygame.draw.ellipse(screen, edge, _rect(x, y, s, (0.23, 0.72, 0.54, 0.16)))
    pygame.draw.ellipse(screen, fill, _rect(x, y, s, (0.27, 0.73, 0.46, 0.10)))
    pygame.draw.rect(screen, edge, _rect(x, y, s, (0.32, 0.62, 0.36, 0.13)), border_radius=max(2, s // 20))
    pygame.draw.rect(screen, fill, _rect(x, y, s, (0.35, 0.63, 0.30, 0.08)), border_radius=max(2, s // 24))
    pygame.draw.line(screen, shade, (int(x + 0.33 * s), int(y + 0.79 * s)), (int(x + 0.67 * s), int(y + 0.79 * s)), max(1, s // 36))


def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


class _SoundEffects:
    def __init__(self, pygame):
        self.enabled = False
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self.sounds = {
                "select": self._tone(pygame, 660, 0.045, 0.18),
                "place": self._tone(pygame, 420, 0.075, 0.22),
                "capture": self._tone(pygame, 180, 0.11, 0.30),
            }
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def play(self, name: str) -> None:
        if self.enabled and name in self.sounds:
            self.sounds[name].play()

    @staticmethod
    def _tone(pygame, freq: float, duration: float, volume: float):
        sample_rate = 44100
        n = int(sample_rate * duration)
        samples = array.array("h")
        for i in range(n):
            fade = 1.0 - (i / max(1, n))
            val = int(32767 * volume * fade * math.sin(2.0 * math.pi * freq * i / sample_rate))
            samples.append(val)
        return pygame.mixer.Sound(buffer=samples.tobytes())


def _new_animation(board: chess.Board, move: chess.Move, was_capture: bool) -> dict | None:
    piece = board.piece_at(move.to_square)
    if piece is None:
        return None
    return {
        "move": move,
        "piece": piece,
        "start": time.perf_counter(),
        "duration": 0.24 if was_capture else 0.20,
        "capture": was_capture,
    }


def _wrap_text(font, text: str, max_width: int) -> list[str]:
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


def _draw_ring(pygame, screen, square: int, square_size: int, human_color: bool, color, width: int = 4) -> None:
    x, y = _square_to_xy(square, square_size, human_color)
    pad = max(4, square_size // 12)
    rect = (x + pad, y + pad, square_size - 2 * pad, square_size - 2 * pad)
    pygame.draw.rect(screen, color, rect, width=width, border_radius=max(4, square_size // 10))


def run_gui(
    agent,
    human_color: bool = chess.WHITE,
    square_size: int = 64,
    difficulty_label: str | None = None,
    explainer=None,
) -> None:
    """Loop GUI chính. Block cho đến khi cửa sổ đóng.

    ``explainer`` là một ``MoveExplainer`` (tuỳ chọn): bật giải thích XAI trực
    tiếp. Caller chịu trách nhiệm gọi ``explainer.close()`` sau khi hàm trả về.
    """
    import pygame
    pygame.init()
    pygame.display.set_caption("Chess AI Self-play — VLU đồ án")

    board_px = 8 * square_size
    status_h = 160
    screen = pygame.display.set_mode((board_px, board_px + status_h))
    clock = pygame.time.Clock()
    status_font = pygame.font.SysFont("dejavusans", 14)
    sound = _SoundEffects(pygame)

    env = ChessEnv()
    selected: Optional[int] = None
    last_move: Optional[chess.Move] = None
    hint_move: Optional[chess.Move] = None
    hint_info = "H = gợi ý nước đi"
    explain_lines: list[str] = []
    ai_info = {"move": "-", "time": 0.0, "nodes": 0, "depth": "-"}
    animation = None
    ply = 0
    reports: dict[int, dict] = {}
    show_summary = False
    summary_cache: tuple[int, list[str]] = (0, [])

    # Mọi phân tích XAI đi qua đúng một worker thread: SimpleEngine không
    # thread-safe, còn UI thì không được phép đứng chờ engine.
    xai_requests: Optional[queue.Queue] = None
    xai_responses: queue.Queue = queue.Queue()
    if explainer is not None:
        xai_requests = queue.Queue()

        def xai_worker() -> None:
            while True:
                item = xai_requests.get()
                if item[0] == "stop":
                    break
                try:
                    if item[0] == "move":
                        _, req_ply, fen, uci = item
                        report = explainer.analyze_move(chess.Board(fen), uci)
                        xai_responses.put(("move", req_ply, report))
                    elif item[0] == "hint":
                        _, fen = item
                        xai_responses.put(("hint", fen, explainer.suggest_move(chess.Board(fen))))
                except Exception as exc:  # báo lỗi lên UI thay vì chết im lặng
                    xai_responses.put(("error", None, str(exc)))

        threading.Thread(target=xai_worker, daemon=True).start()

    running = True
    while running:
        now = time.perf_counter()
        if animation and now - animation["start"] >= animation["duration"]:
            animation = None

        # --- Nhận kết quả phân tích từ worker ---
        while True:
            try:
                kind, key, payload = xai_responses.get_nowait()
            except queue.Empty:
                break
            if kind == "move":
                reports[key] = payload
                if key == ply:  # chỉ hiện giải thích cho nước mới nhất
                    text = f"{payload['move_san']} — {payload['quality_vi']}: {payload['explanation_vi']}"
                    explain_lines = _wrap_text(status_font, text, board_px - 16)[:3]
            elif kind == "hint":
                if payload and env.board.fen() == key:
                    suggested = chess.Move.from_uci(payload["move_uci"])
                    if suggested in env.board.legal_moves:
                        hint_move = suggested
                        chance = payload.get("win_chance")
                        chance_text = f" | thắng ~{chance:.0f}%" if chance is not None else ""
                        hint_info = f"Gợi ý: {payload['move_san']}{chance_text}"
                        if payload.get("line_san"):
                            explain_lines = _wrap_text(
                                status_font, f"Biến chính: {payload['line_san']}", board_px - 16
                            )[:2]
            elif kind == "error":
                explain_lines = _wrap_text(status_font, f"Lỗi phân tích: {payload}", board_px - 16)[:2]

        # --- Vẽ bàn cờ ---
        screen.fill(BG)
        for sq in chess.SQUARES:
            x, y = _square_to_xy(sq, square_size, human_color)
            light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
            color = LIGHT if light else DARK
            if last_move and sq in (last_move.from_square, last_move.to_square):
                color = LAST_MOVE
            if selected == sq:
                color = HIGHLIGHT
            pygame.draw.rect(screen, color, (x, y, square_size, square_size))

            if selected is not None and sq in _legal_targets(env.board, selected):
                pygame.draw.circle(
                    screen,
                    LEGAL_DOT,
                    (x + square_size // 2, y + square_size // 2),
                    max(5, square_size // 10),
                )

            piece = env.board.piece_at(sq)
            if animation and sq == animation["move"].to_square:
                piece = None
            if piece:
                _draw_piece(pygame, screen, piece, x, y, square_size)

        if animation:
            move = animation["move"]
            from_x, from_y = _square_to_xy(move.from_square, square_size, human_color)
            to_x, to_y = _square_to_xy(move.to_square, square_size, human_color)
            t = _ease_out_cubic((now - animation["start"]) / animation["duration"])
            px = from_x + (to_x - from_x) * t
            py = from_y + (to_y - from_y) * t
            _draw_piece(pygame, screen, animation["piece"], px, py, square_size)

        if hint_move is not None and hint_move in env.board.legal_moves:
            _draw_ring(pygame, screen, hint_move.from_square, square_size, human_color, HINT_FROM)
            _draw_ring(pygame, screen, hint_move.to_square, square_size, human_color, HINT_TO)

        # --- Tổng kết ván (overlay phủ bàn cờ, bật/tắt bằng T) ---
        if show_summary and reports:
            if summary_cache[0] != len(reports):
                summary = summarize_game([reports[k] for k in sorted(reports)])
                summary_cache = (len(reports), format_summary_vi(summary))
            overlay = pygame.Surface((board_px, board_px), pygame.SRCALPHA)
            overlay.fill((25, 28, 34, 236))
            screen.blit(overlay, (0, 0))
            heading = status_font.render("TỔNG KẾT VÁN (T để đóng)", True, ACCENT)
            screen.blit(heading, (16, 18))
            y = 48
            for line in summary_cache[1]:
                for text_line in _wrap_text(status_font, line, board_px - 32)[:3]:
                    screen.blit(status_font.render(text_line, True, TEXT), (16, y))
                    y += 21
                y += 6

        # --- Status bar ---
        turn_str = "Trắng" if env.board.turn == chess.WHITE else "Đen"
        result_str = env.result() if env.is_terminal() else "đang chơi"
        mode = f"   |   Độ khó: {difficulty_label}" if difficulty_label else ""
        if explain_lines:
            explain_block = explain_lines
        elif explainer is not None:
            explain_block = ["Giải thích sẽ hiện sau mỗi nước đi."]
        else:
            explain_block = ["Explain: AB / Q / confidence sẽ hiện sau gợi ý hoặc nước AI."]
        help_line = "Click 2 lần để đi. H = gợi ý. ESC = thoát."
        if explainer is not None:
            help_line = "Click 2 lần để đi. H = gợi ý. T = tổng kết ván. ESC = thoát."
        hint_line = hint_info
        if env.is_terminal() and reports and not show_summary:
            hint_line = "Ván kết thúc — bấm T để xem tổng kết và rút kinh nghiệm."
        lines = [
            f"Lượt: {turn_str}   |   Kết quả: {result_str}{mode}",
            f"AI: {ai_info['move']}   |   depth={ai_info['depth']}   nodes={ai_info['nodes']}   {ai_info['time']:.2f}s",
            f"{hint_line}",
            *explain_block,
            help_line,
        ]
        for i, line in enumerate(lines):
            color = MUTED if i == len(lines) - 1 else TEXT
            surf = status_font.render(line, True, color)
            screen.blit(surf, (8, board_px + 4 + i * 21))

        pygame.display.flip()

        # --- Event handling ---
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_t and reports:
                show_summary = not show_summary
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_h:
                if animation is None and not env.is_terminal() and env.board.turn == human_color:
                    if xai_requests is not None:
                        xai_requests.put(("hint", env.board.fen()))
                        hint_info = "Đang tính gợi ý..."
                    else:
                        start = time.perf_counter()
                        hint_move = agent.choose_move(env)
                        elapsed = time.perf_counter() - start
                        if hint_move is None:
                            hint_info = "Gợi ý: không có nước hợp lệ"
                            explain_lines = []
                        else:
                            hint_info = f"Gợi ý: {env.san(hint_move)} ({hint_move.uci()})   {elapsed:.2f}s"
                            explain_lines = [_format_explanation(getattr(agent, "last_explanation", None))]
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if animation is not None or show_summary:
                    continue
                if env.is_terminal() or env.board.turn != human_color:
                    continue
                sq = _xy_to_square(ev.pos[0], ev.pos[1], square_size, human_color)
                if sq is None:
                    continue
                if selected is None:
                    # chọn nguồn — chỉ chọn được quân của mình
                    piece = env.board.piece_at(sq)
                    if piece and piece.color == human_color:
                        selected = sq
                        sound.play("select")
                else:
                    # thử đẩy nước
                    move = _candidate_move(env.board, selected, sq)
                    if move in env.legal_moves():
                        fen_before = env.board.fen()
                        was_capture = env.board.is_capture(move)
                        env.push(move)
                        ply += 1
                        last_move = move
                        animation = _new_animation(env.board, move, was_capture)
                        sound.play("capture" if was_capture else "place")
                        hint_move = None
                        hint_info = "H = gợi ý nước đi"
                        if xai_requests is not None:
                            xai_requests.put(("move", ply, fen_before, move.uci()))
                            explain_lines = ["Đang phân tích nước của bạn..."]
                        else:
                            explain_lines = []
                    selected = None

        # --- AI tới phiên ---
        if running and animation is None and not env.is_terminal() and env.board.turn != human_color:
            pygame.display.flip()
            start = time.perf_counter()
            ai_move = agent.choose_move(env)
            elapsed = time.perf_counter() - start
            if ai_move is None:
                continue
            fen_before = env.board.fen()
            was_capture = env.board.is_capture(ai_move)
            env.push(ai_move)
            ply += 1
            last_move = ai_move
            animation = _new_animation(env.board, ai_move, was_capture)
            sound.play("capture" if was_capture else "place")
            hint_move = None
            hint_info = "H = gợi ý nước đi"
            if xai_requests is not None:
                xai_requests.put(("move", ply, fen_before, ai_move.uci()))
                explain_lines = ["Đang phân tích nước của AI..."]
            else:
                explain_lines = [_format_explanation(getattr(agent, "last_explanation", None))]
            stats = getattr(agent, "last_stats", None)
            info = getattr(agent, "last_info", None)
            depth_str = "-"
            if info:
                depth_str = str(info[-1]["depth"])
            elif hasattr(agent, "depth"):
                depth_str = str(agent.depth)
            ai_info = {
                "move": ai_move.uci(),
                "time": elapsed,
                "nodes": getattr(stats, "visited", 0) if stats else 0,
                "depth": depth_str,
            }

        clock.tick(30)

    if xai_requests is not None:
        xai_requests.put(("stop",))
    pygame.quit()


def _format_explanation(explanation) -> str:
    if not explanation:
        return ""
    base = (
        f"AB={explanation['alphabeta_score']:.0f} "
        f"Q={explanation['q_value']:.2f} "
        f"cf={explanation['confidence']:.2f} "
        f"QB={explanation['q_bonus']:.2f}"
    )
    if explanation.get("memory_hit"):
        base += " MEM=hit"
    if explanation.get("mcts_visits", 0):
        base += (
            f" MC={explanation['mcts_score']:.2f}"
            f"/{explanation['mcts_visits']} MB={explanation['mcts_bonus']:.1f}"
        )
    return f"Explain: {base} final={explanation['final_score']:.0f}"

