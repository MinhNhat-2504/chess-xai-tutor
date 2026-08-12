"""Tính ELO rating từ kết quả tournament — Báo cáo mục 4.4.4.

Công thức ELO chuẩn:
    expected_A = 1 / (1 + 10^((rating_B - rating_A) / 400))
    new_A = rating_A + k * (score_A - expected_A)

`score_A` ∈ {0 = thua, 0.5 = hoà, 1 = thắng}.
"""
from __future__ import annotations


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def update_elo(rating_a: float, rating_b: float, score_a: float, k: float = 32.0):
    """Trả về (new_rating_a, new_rating_b)."""
    e_a = expected_score(rating_a, rating_b)
    e_b = 1.0 - e_a
    score_b = 1.0 - score_a
    return rating_a + k * (score_a - e_a), rating_b + k * (score_b - e_b)


def compute_ratings(games_rows, initial: float = 1500.0, k: float = 32.0) -> dict[str, float]:
    """Cập nhật ELO tuần tự theo từng ván trong `games_rows`.

    `games_rows`: iterable of dict có các khoá `white, black, winner`
                  (winner ∈ {white_name, black_name, "draw"}).
    """
    ratings: dict[str, float] = {}

    for row in games_rows:
        w, b = row["white"], row["black"]
        ratings.setdefault(w, initial)
        ratings.setdefault(b, initial)

        winner = row["winner"]
        if winner == w:
            score_w = 1.0
        elif winner == b:
            score_w = 0.0
        else:
            score_w = 0.5

        ratings[w], ratings[b] = update_elo(ratings[w], ratings[b], score_w, k=k)

    return ratings
