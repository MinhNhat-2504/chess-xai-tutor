# Ánh xạ Cấu trúc Repo ↔ Báo cáo

Tài liệu phân công chi tiết: xem `docs/TASK_ASSIGNMENT.md`.

## Rule - Skill - Task

| Nhóm | Nội dung chính | Tài liệu chi tiết |
|---|---|---|
| Rule | Quy tắc sửa code, phạm vi module, cách chạy test, quy ước không commit artifact | `docs/TASK_ASSIGNMENT.md` mục "Rule làm việc" |
| Skill | Kỹ năng cần có cho từng mảng: luật cờ, heuristic, tìm kiếm, Q-learning, thực nghiệm, demo | `docs/TASK_ASSIGNMENT.md` mục "Skill cần có" |
| Task | Ai phụ trách file nào, đầu ra cần bàn giao, checklist hoàn thành | `docs/TASK_ASSIGNMENT.md` mục "Task theo thành viên" |
| Novelty | Research gap, tính mới, đóng góp kỹ thuật/thực nghiệm/demo | `docs/NOVELTY_CONTRIBUTION.md` |

| Thư mục / file | Vai trò | Mục báo cáo |
|---|---|---|
| `docs/NOVELTY_CONTRIBUTION.md` | Tính mới, contribution, cách viết/cách bảo vệ | 1.4, 1.5, 5.2 |
| `src/board/chess_env.py` | Biểu diễn bàn cờ, sinh nước đi, luật đặc biệt | 2.2, 3.3 |
| `src/board/state.py` | Mã hóa trạng thái cho Q-table (FEN rút gọn + feature_vector) | 3.6.1 |
| `src/board/compact_state.py` | **(mới)** Bucket feature_vector → state key gọn cho Q-learning | 3.6.1 mở rộng |
| `src/board/state_resolver.py` | **(mới)** Chọn state key `full` / `compact` nhất quán cho train/evaluate/play | 3.6.1, 4.4.5 |
| `src/search/minimax.py` | Minimax thuần (Mô hình 1) — **không sửa, giữ làm baseline** | 2.3, 3.8.1 |
| `src/search/alphabeta.py` | Alpha-Beta + đếm node + hook cho quiescence/killer/history | 2.4, 3.8.2, 4.4.3 |
| `src/search/move_ordering.py` | Sắp xếp nước đi (MVV-LVA + killer + history) | 2.4.2 |
| `src/search/transposition.py` | **(mới)** TT với bound flag EXACT/LOWER/UPPER + best_move (PV ordering) | 2.4.5 |
| `src/search/quiescence.py` | **(mới)** Quiescence search chống horizon effect | 2.4.3 |
| `src/search/heuristics.py` | **(mới)** Killer-moves & History heuristic | 2.4.2 mở rộng |
| `src/search/iterative_deepening.py` | **(mới)** Iterative deepening + time control + PV-reuse | 2.4.4 |
| `src/evaluation/evaluator.py` | Hàm đánh giá vị trí | 2.6, 3.5 |
| `src/evaluation/piece_tables.py` | Giá trị quân, piece-square table | 3.5 |
| `src/rl/q_learning.py` | Q-Learning, Bellman update, optional quantized Q-value | 2.5, 3.6, 4.4.5 |
| `src/rl/reward.py` | Reward shaping đa tầng | 3.6.2 |
| `src/rl/replay.py` | Lưu trữ kinh nghiệm | 3.6.3, 4.3.1 |
| `src/rl/batch_update.py` | **(mới)** Mini-batch update off-policy từ ReplayBuffer | 3.6.3 |
| `src/agents/minimax_agent.py` | Wrapper Mô hình 1 — **không sửa** | 3.8.1 |
| `src/agents/alphabeta_agent.py` | Wrapper Mô hình 2 — wire cờ quiescence/ID/killer/history | 3.8.2 |
| `src/agents/hybrid_agent.py` | Hàm đánh giá lai, confidence-aware Q bonus, explainable score | 3.7, 3.8.3, 4.4.5 |
| `src/training/self_play.py` | Vòng huấn luyện self-play + replay batch + tqdm | 2.5.4, 4.3 |
| `src/analytics/pgn_writer.py` | **(mới)** Xuất ván cờ ra PGN chuẩn | 4.5 |
| `src/analytics/elo.py` | **(mới)** Tính ELO rating tuần tự | 4.4.4 |
| `src/analytics/plots.py` | **(mới)** matplotlib — biểu đồ training + evaluation | 4.6 |
| `src/ui/app.py` | Giao diện console | 3.9 |
| `src/ui/pygame_app.py` | **(mới)** Giao diện Pygame GUI | 3.9 |
| `scripts/train.py` | Chạy huấn luyện | 4.3 |
| `scripts/evaluate.py` | So sánh 3 mô hình, xuất CSV/JSON/PGN/ELO, opening benchmark | 4.4, 4.5 |
| `scripts/plot_results.py` | **(mới)** Render lại biểu đồ từ artifact đã có | 4.6 |
| `experiments/`, `notebooks/` | Kết quả, biểu đồ, phân tích | 4.6 |
