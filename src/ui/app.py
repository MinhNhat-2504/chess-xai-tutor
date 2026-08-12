"""Minimal console UI for playing against one agent."""
import chess
import time

from ..board.chess_env import ChessEnv


def run(agent, human_color=chess.WHITE):
    """Play one game against `agent`."""
    env = ChessEnv()
    side = "trang" if human_color == chess.WHITE else "den"
    print(f"Ban cam quan {side}. Nhap UCI (vd: e2e4) hoac SAN (vd: Nf3). Go 'quit' de thoat.")

    while not env.is_terminal():
        print()
        print(env.board.unicode(invert_color=False, borders=True))
        print(f"FEN: {env.fen()}")

        if env.board.turn == human_color:
            raw = input("Ban di: ").strip()
            if raw.lower() in {"q", "quit", "exit"}:
                print("Da thoat van choi.")
                return
            try:
                move = env.board.parse_uci(raw)
            except ValueError:
                try:
                    move = env.board.parse_san(raw)
                except ValueError:
                    print("Nuoc di khong hop le, thu lai.")
                    continue
            if move not in env.legal_moves():
                print("Nuoc di khong nam trong danh sach hop le.")
                continue
            env.push(move)
        else:
            start = time.perf_counter()
            move = agent.choose_move(env)
            elapsed = time.perf_counter() - start
            if move is None:
                break
            print(f"AI di: {env.san(move)} ({move.uci()}) | {elapsed:.2f}s")
            explanation = getattr(agent, "last_explanation", None)
            if explanation:
                print(_format_explanation(explanation))
            env.push(move)

    print()
    print(env.board.unicode(invert_color=False, borders=True))
    print(f"Ket qua: {env.result()}")


def _format_explanation(explanation) -> str:
    parts = ["  explain:"]
    if "difficulty" in explanation:
        parts.append(f"level={explanation['difficulty']}")
    if "difficulty_rank" in explanation:
        parts.append(f"rank={explanation['difficulty_rank']}")
    if explanation.get("memory_hit"):
        parts.append("memory=hit")
    if "alphabeta_score" in explanation:
        parts.append(f"AB={explanation['alphabeta_score']:.2f}")
    if "minimax_score" in explanation:
        parts.append(f"MM={explanation['minimax_score']:.2f}")
    if "q_value" in explanation:
        parts.append(f"Q={explanation['q_value']:.2f}")
    if "confidence" in explanation:
        parts.append(f"conf={explanation['confidence']:.2f}")
    if "q_bonus" in explanation:
        parts.append(f"bonus={explanation['q_bonus']:.2f}")
    if "mcts_bonus" in explanation:
        parts.append(f"mcts={explanation['mcts_bonus']:.2f}")
    if "final_score" in explanation:
        parts.append(f"final={explanation['final_score']:.2f}")
    return " ".join(parts)
