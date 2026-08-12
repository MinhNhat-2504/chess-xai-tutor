"""Giải thích nước đi và phân tích ván cờ cho người học."""

from .engine_oracle import StockfishOracle, find_stockfish
from .explainer import MoveExplainer
from .game_summary import format_summary_vi, summarize_game
from .motifs import Motif, detect_motifs

__all__ = [
    "MoveExplainer", "StockfishOracle", "find_stockfish",
    "Motif", "detect_motifs",
    "summarize_game", "format_summary_vi",
]
