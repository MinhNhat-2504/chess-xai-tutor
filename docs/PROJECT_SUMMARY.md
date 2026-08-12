# Tổng Hợp Đồ Án Chess AI Self-play

Tên đề tài:

> Ứng dụng Minimax, Alpha-Beta Pruning và Confidence-Aware Quantized Q-Learning trong xây dựng AI cờ vua tự cải thiện qua Self-play

Sinh viên thực hiện:

- Nguyễn Thành Phong - 2474802010304
- Trần An Kỳ - 2474802010460

Giảng viên hướng dẫn:

- ThS. Phan Hồ Viết Trường

---

## 1. Mục Tiêu Đồ Án

Đồ án xây dựng và đánh giá một hệ thống AI chơi cờ vua gồm ba mô hình:

| Model | Tên mô hình | Mục đích |
|---|---|---|
| Model 1 | Minimax | Baseline tìm kiếm cơ bản |
| Model 2 | Alpha-Beta | Tối ưu Minimax bằng cắt tỉa |
| Model 3 | Hybrid Alpha-Beta + Q-Learning | Kết hợp tìm kiếm với kinh nghiệm self-play |

Mục tiêu chính:

- Cài đặt AI cờ vua có thể chọn nước hợp lệ.
- So sánh Minimax, Alpha-Beta và Hybrid.
- Huấn luyện Q-learning bằng self-play.
- Đánh giá bằng ELO, win/loss/draw, thời gian, node visited/pruned.
- Xây dựng giao diện chơi cờ và gợi ý nước đi.
- Đề xuất novelty dựa trên Confidence-Aware Quantized Q-Learning.

---

## 2. Research Gap

Q-learning dạng bảng khó áp dụng trực tiếp cho cờ vua vì không gian trạng thái và hành động cực lớn.

Nếu dùng FEN làm state key, Q-table sẽ tăng rất nhanh nhưng nhiều state chỉ xuất hiện một vài lần. Điều này gây ra:

- State-action explosion.
- Kinh nghiệm self-play khó tái sử dụng.
- Q-value dễ nhiễu nếu state/action ít được cập nhật.

Đồ án kiểm tra hướng giải quyết:

- Rút gọn state bằng compact feature binning.
- Lượng tử hóa Q-value bằng clip và rounding.
- Dùng confidence dựa trên số lần học `N(s,a)`.

---

## 3. Novelty Và Contribution

Đồ án đề xuất biến thể:

```text
Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning
```

Công thức chọn nước:

```text
FinalScore = AlphaBetaScore + lambda * confidence(s,a) * Q(s,a)
confidence(s,a) = N(s,a) / (N(s,a) + k)
```

Trong đó:

- `AlphaBetaScore`: điểm từ tìm kiếm Alpha-Beta.
- `Q(s,a)`: Q-value học từ self-play.
- `N(s,a)`: số lần Q-table cập nhật cặp state-action.
- `confidence(s,a)`: mức tin cậy của Q-value.
- `lambda`: hệ số điều chỉnh ảnh hưởng của Q-learning.
- `k`: hệ số làm mượt confidence.

Đóng góp chính:

- Hybrid AI kết hợp Alpha-Beta và Q-learning.
- Compact state representation để giảm state explosion.
- Quantized Q-value để kiểm tra tác động lượng tử hóa.
- Confidence-aware Q bonus để tránh tin quá mạnh vào Q-value ít dữ liệu.
- Opening robustness benchmark trên nhiều khai cuộc.
- Explainable move recommendation trong UI/console.
- Xuất CSV/JSON/PGN, ELO rating và biểu đồ tự động.

---

## 4. Kiến Trúc Hệ Thống

Hệ thống được chia thành các tầng:

| Tầng | Module | Vai trò |
|---|---|---|
| Board | `src/board/` | Quản lý bàn cờ, FEN, state key |
| Evaluation | `src/evaluation/` | Hàm đánh giá vị trí |
| Search | `src/search/` | Minimax, Alpha-Beta, quiescence, TT |
| Agents | `src/agents/` | Wrapper cho từng mô hình AI |
| RL | `src/rl/` | Q-learning, reward, replay buffer |
| Training | `src/training/` | Self-play training loop |
| Analytics | `src/analytics/` | ELO, PGN, biểu đồ |
| UI | `src/ui/` | Console UI và Pygame UI |
| Scripts | `scripts/` | Train, evaluate, play, plot |

Luồng train:

```text
config.yaml
  -> scripts/train.py
  -> self_play.py
  -> QLearning.update()
  -> q_table.pkl + training_history.csv
```

Luồng evaluate:

```text
config.yaml
  -> scripts/evaluate.py
  -> MinimaxAgent / AlphaBetaAgent / HybridAgent
  -> games.csv + summary.json + elo.json + games.pgn
```

Luồng demo:

```text
scripts/play.py
  -> Console UI hoặc Pygame UI
  -> Agent chọn nước
  -> Hiển thị bàn cờ, gợi ý và explainable score
```

---

## 5. Các Thuật Toán Chính

### 5.1 Minimax

Minimax duyệt cây trò chơi theo độ sâu cố định. Một bên tối đa hóa điểm, bên còn lại tối thiểu hóa điểm.

Độ phức tạp:

```text
O(b^d)
```

Trong đó:

- `b`: branching factor.
- `d`: độ sâu tìm kiếm.

### 5.2 Alpha-Beta Pruning

Alpha-Beta tối ưu Minimax bằng cách bỏ qua các nhánh không thể ảnh hưởng đến kết quả cuối.

Điều kiện cắt tỉa:

```text
MAX cutoff khi alpha >= beta
MIN cutoff khi beta <= alpha
```

### 5.3 Move Ordering

Nước đi được sắp xếp để Alpha-Beta cắt tỉa tốt hơn:

- Capture theo MVV-LVA.
- Promotion.
- Check.
- Castling.
- Killer move.
- History heuristic.

### 5.4 Transposition Table

Lưu kết quả tìm kiếm theo state để tái sử dụng.

Mỗi entry gồm:

```text
depth, score, flag, best_move
```

Flag:

- `EXACT`
- `LOWER`
- `UPPER`

### 5.5 Quiescence Search

Khi đến leaf, nếu vị trí còn "ồn" như capture/check/promotion, tiếp tục tìm kiếm các nước ồn để giảm horizon effect.

### 5.6 Q-Learning

Công thức Bellman update:

```text
Q(s,a) <- Q(s,a) + alpha * [r + gamma * max Q(s',a') - Q(s,a)]
```

### 5.7 Quantized Q-Value

Sau Bellman update:

```text
Q_clip = clip(Q_raw, -C, C)
Q_quant = step * round(Q_clip / step)
```

Nếu không bật `q_value_step`, Q-value giữ dạng float.

### 5.8 Confidence-Aware Hybrid

Hybrid không dùng Q-value một cách mù quáng. Q-value chỉ ảnh hưởng mạnh nếu đã được học đủ nhiều:

```text
confidence(s,a) = N(s,a) / (N(s,a) + k)
FinalScore = AlphaBetaScore + lambda * confidence(s,a) * Q(s,a)
```

---

## 6. Hàm Đánh Giá Vị Trí

Hàm đánh giá tổng hợp:

```text
Score = Material + Mobility + KingSafety + CenterControl
      + PawnStructure + Development + Threat + CheckBonus
```

Các thành phần:

- Material.
- Piece-square table.
- Mobility.
- King safety.
- Center control.
- Pawn structure.
- Development.
- Threat/hanging piece.
- Check/checkmate/stalemate.

Chi tiết công thức nằm trong:

```text
docs/CONG_THUC.md
```

---

## 7. Training Self-play

Mỗi ván self-play tạo transition:

```text
(s, a, r, s_next, next_actions)
```

Reward gồm:

```text
r = terminal_reward + shaping_reward + move_reward
```

Trong đó:

- `terminal_reward`: thắng/thua/hòa.
- `shaping_reward`: thay đổi điểm đánh giá vị trí.
- `move_reward`: capture, promotion, check.

Training history ghi:

- `q_size`
- `unique_states`
- `actions_per_state`
- `mean_abs_q`
- `epsilon`
- `replay_size`
- `replay_updates`

---

## 8. Thực Nghiệm

### 8.1 Metric Đánh Giá

- Win/loss/draw.
- ELO.
- Avg time per move.
- Nodes visited.
- Nodes pruned.
- Cache hits.
- Q-table size.
- Unique states.
- Actions per state.

### 8.2 Opening Robustness Benchmark

Benchmark đa khai cuộc gồm:

- Start position.
- Italian Game.
- Sicilian Defense.
- French Defense.
- Queen's Gambit.
- King's Indian.

Lệnh chạy:

```bash
python scripts/evaluate.py --config config/config.yaml --games 2 --depth 2 --max-moves 80 --q-table data/q_tables/q_quantized.pkl --state-representation compact --openings suite
```

### 8.3 Kết Quả Nổi Bật

Benchmark đa khai cuộc với quantized compact Q-table:

| Model | ELO |
|---|---:|
| Hybrid Confidence + Quantized | 1561 |
| Alpha-Beta | 1560 |
| Minimax | 1379 |

Nhận xét:

- Hybrid vượt rõ Minimax.
- Hybrid đạt mức xấp xỉ Alpha-Beta.
- Confidence-aware Q bonus giúp Q-learning ảnh hưởng có kiểm soát.
- Compact + quantized Q-value không làm mô hình mất sức chơi đáng kể.

---

## 9. Giao Diện Demo

### 9.1 Console UI

Chạy:

```bash
python scripts/play.py --agent hybrid --depth 2 --q-table data/q_tables/q_table.pkl
```

Tính năng:

- Nhập nước bằng UCI hoặc SAN.
- AI phản hồi nước đi.
- In explainable score nếu dùng Hybrid.

### 9.2 Pygame UI

Chạy:

```bash
python scripts/play.py --ui pygame --agent hybrid --depth 2 --q-table data/q_tables/q_table.pkl
```

Tính năng:

- Hiển thị bàn cờ trực quan.
- Highlight nước hợp lệ.
- Nhấn `H` để xem gợi ý.
- Hiển thị AlphaBetaScore, QValue, confidence, Q bonus, FinalScore.

---

## 10. Lệnh Chạy Chính

### 10.1 Cài Đặt

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 10.2 Train Mặc Định

```bash
python scripts/train.py --config config/config.yaml
```

### 10.3 Train Quantized Compact Q

```bash
python scripts/train.py --config config/config.yaml --games 500 --max-moves 80 --save-every 100 --state-representation compact --q-value-step 0.05 --q-value-clip 5.0 --q-table data/q_tables/q_quantized.pkl --history experiments/results/history_quantized.csv --seed 7
```

### 10.4 Evaluate

```bash
python scripts/evaluate.py --config config/config.yaml --games 2 --depth 2 --max-moves 80 --q-table data/q_tables/q_quantized.pkl --state-representation compact --openings suite
```

### 10.5 Plot

```bash
python scripts/plot_results.py --config config/config.yaml
```

### 10.6 Test

```bash
python -m pytest -q
python -m compileall -q src scripts
```

---

## 11. Cấu Trúc Thư Mục

```text
src/
  agents/
  analytics/
  board/
  evaluation/
  rl/
  search/
  training/
  ui/
scripts/
  train.py
  evaluate.py
  play.py
  plot_results.py
docs/
  CONG_THUC.md
  NOVELTY_CONTRIBUTION.md
  REPORT_OUTLINE.md
  STRUCTURE.md
  TASK_ASSIGNMENT.md
```

---

## 12. Kiểm Thử

Test suite hiện tại:

```text
64 passed
```

Nhóm test:

- Board rules.
- Search.
- Q-learning.
- Compact state.
- Batch update.
- Transposition table.
- Quiescence search.
- Iterative deepening.
- PGN/ELO.
- Plot generation.
- Pygame helper.
- Opening benchmark.

---

## 13. Kết Luận

Đồ án đã xây dựng thành công hệ thống AI cờ vua gồm ba mô hình Minimax, Alpha-Beta và Hybrid.

Biến thể đề xuất **Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning** giúp:

- Kết hợp tìm kiếm đối kháng với học tăng cường.
- Giảm vấn đề state-action explosion bằng compact state.
- Kiểm tra ảnh hưởng của quantized Q-value.
- Điều chỉnh tác động Q-learning bằng confidence.
- Đánh giá mô hình trên benchmark đa khai cuộc.
- Cung cấp giao diện demo có giải thích nước đi.

Kết quả thực nghiệm cho thấy Hybrid Confidence + Quantized vượt rõ Minimax và đạt mức xấp xỉ Alpha-Beta trong benchmark đa khai cuộc.

---

## 14. Hướng Phát Triển

- Dùng Deep Q-Network thay cho Q-table.
- Dùng policy/value network.
- Kết hợp Monte Carlo Tree Search.
- Bổ sung opening book.
- Bổ sung endgame tablebase.
- Parallel search.
- Cải thiện UI và phân tích ván đấu.

---

## 15. Tài Liệu Liên Quan Trong Repo

| File | Nội dung |
|---|---|
| `README.md` | Hướng dẫn chạy và tóm tắt project |
| `docs/REPORT_OUTLINE.md` | Outline Word/báo cáo |
| `docs/CONG_THUC.md` | Công thức chi tiết |
| `docs/NOVELTY_CONTRIBUTION.md` | Novelty và contribution |
| `docs/STRUCTURE.md` | Ánh xạ module |
| `docs/TASK_ASSIGNMENT.md` | Rule, skill, task |
| `docs/architecture/architecture.pdf` | Sơ đồ kiến trúc |
