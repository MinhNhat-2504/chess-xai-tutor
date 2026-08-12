"""Giao diện chung cho mọi agent."""
from abc import ABC, abstractmethod
import chess


class BaseAgent(ABC):
    @abstractmethod
    def choose_move(self, env) -> chess.Move | None:
        ...
