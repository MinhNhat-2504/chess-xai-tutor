# Outline Báo Cáo Đồ Án

Tên đề tài:

> Ứng dụng Minimax, Alpha-Beta Pruning và Confidence-Aware Quantized Q-Learning trong xây dựng AI cờ vua tự cải thiện qua Self-play

Tài liệu này là outline đề xuất để cập nhật file Word báo cáo. Có thể copy trực tiếp các đề mục sang Word, sau đó lấy nội dung chi tiết từ các file:

- `docs/CONG_THUC.md`
- `docs/NOVELTY_CONTRIBUTION.md`
- `docs/STRUCTURE.md`
- `docs/TASK_ASSIGNMENT.md`
- `docs/architecture/architecture.pdf`

---

# Trang Bìa

- Trường / Khoa
- Tên môn học: Nhập môn Trí tuệ nhân tạo
- Tên đề tài
- Sinh viên thực hiện:
  - Nguyễn Thành Phong - 2474802010304
  - Trần An Kỳ - 2474802010460
- Giảng viên hướng dẫn
- Thời gian thực hiện

# Lời Cảm Ơn

# Tóm Tắt

- Mục tiêu của đồ án
- Ba mô hình được xây dựng
- Biến thể đề xuất
- Kết quả nổi bật
- Từ khóa

# Mục Lục

# Danh Mục Hình

# Danh Mục Bảng

# Danh Mục Từ Viết Tắt

| Từ viết tắt | Ý nghĩa |
|---|---|
| AI | Artificial Intelligence |
| RL | Reinforcement Learning |
| QL | Q-Learning |
| AB | Alpha-Beta |
| TT | Transposition Table |
| FEN | Forsyth-Edwards Notation |
| PGN | Portable Game Notation |
| ELO | Hệ thống xếp hạng sức mạnh |

---

# Chương 1. Giới Thiệu

## 1.1 Bối Cảnh Đề Tài

- Cờ vua là môi trường tiêu biểu cho bài toán tìm kiếm đối kháng.
- Các thuật toán cổ điển như Minimax và Alpha-Beta vẫn là nền tảng quan trọng.
- Q-learning cho phép mô hình học từ trải nghiệm self-play.
- Vấn đề chính: không gian trạng thái cờ vua rất lớn.

## 1.2 Lý Do Chọn Đề Tài

- Cờ vua dễ minh họa thuật toán AI.
- Có thể so sánh trực tiếp nhiều mô hình.
- Có thể kết hợp tìm kiếm đối kháng với học tăng cường.
- Có thể xây dựng demo trực quan.

## 1.3 Mục Tiêu Đề Tài

- Xây dựng Model 1: Minimax cơ bản.
- Xây dựng Model 2: Minimax + Alpha-Beta Pruning.
- Xây dựng Model 3: Hybrid Alpha-Beta + Q-Learning.
- Huấn luyện Q-learning bằng self-play.
- Đánh giá bằng win/loss/draw, thời gian, node, ELO.
- Xây dựng giao diện chơi cờ và gợi ý nước đi.

## 1.4 Research Gap

- Q-learning dạng bảng gặp vấn đề state-action explosion trong cờ vua.
- FEN rút gọn vẫn tạo số lượng state rất lớn.
- Q-value ít được tái sử dụng nếu mỗi state chỉ xuất hiện một vài lần.
- Cần kiểm tra compact state, quantized Q-value và confidence-aware Q bonus.

## 1.5 Đóng Góp Và Tính Mới Của Đề Tài

### 1.5.1 Đóng Góp Chính

- Đề xuất biến thể Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning.
- Kết hợp Alpha-Beta search với Q-learning self-play.
- Sử dụng compact state representation để giảm state explosion.
- Sử dụng quantized Q-value để kiểm tra tác động lượng tử hóa.
- Dùng confidence dựa trên số lần học `N(s,a)`.

### 1.5.2 Đóng Góp Thực Nghiệm

- Benchmark đa khai cuộc.
- ELO rating tuần tự.
- PGN export.
- Biểu đồ training/evaluation.
- So sánh Minimax, Alpha-Beta, Hybrid.

### 1.5.3 Đóng Góp Demo

- Console UI.
- Pygame UI.
- Highlight nước hợp lệ.
- Gợi ý nước đi.
- Explainable score.

## 1.6 Phạm Vi Đề Tài

- Không xây dựng chess engine đạt chuẩn thi đấu chuyên nghiệp.
- Không dùng neural network hoặc deep reinforcement learning.
- Tập trung vào thuật toán AI cổ điển kết hợp Q-learning dạng bảng.
- Thực nghiệm trong phạm vi số ván và độ sâu phù hợp máy cá nhân.

## 1.7 Cấu Trúc Báo Cáo

---

# Chương 2. Cơ Sở Lý Thuyết

## 2.1 Tổng Quan Bài Toán Cờ Vua

## 2.2 Biểu Diễn Bàn Cờ

### 2.2.1 FEN

### 2.2.2 PGN

### 2.2.3 Sinh Nước Đi Hợp Lệ Bằng `python-chess`

## 2.3 Minimax

### 2.3.1 Ý Tưởng

### 2.3.2 Công Thức Đệ Quy

### 2.3.3 Độ Phức Tạp

## 2.4 Alpha-Beta Pruning

### 2.4.1 Ý Tưởng Cắt Tỉa

### 2.4.2 Điều Kiện Cắt Tỉa

### 2.4.3 Move Ordering

### 2.4.4 Killer Move Và History Heuristic

### 2.4.5 Transposition Table

### 2.4.6 Quiescence Search

### 2.4.7 Iterative Deepening

## 2.5 Q-Learning

### 2.5.1 Khái Niệm State, Action, Reward

### 2.5.2 Công Thức Bellman Update

### 2.5.3 Epsilon-Greedy

### 2.5.4 Epsilon Decay

### 2.5.5 Replay Buffer

### 2.5.6 Batch Update Từ Replay Buffer

## 2.6 Compact State Representation

### 2.6.1 Vấn Đề State Explosion

### 2.6.2 Feature Vector

### 2.6.3 Bucket Feature Vector

## 2.7 Quantized Q-Value

### 2.7.1 Clip Q-Value

### 2.7.2 Làm Tròn Q-Value Theo Bước Lượng Tử

### 2.7.3 Ý Nghĩa Trong Giảm Nhiễu Q-Table

## 2.8 Confidence-Aware Q Bonus

### 2.8.1 Số Lần Học `N(s,a)`

### 2.8.2 Công Thức Confidence

```text
confidence(s,a) = N(s,a) / (N(s,a) + k)
```

### 2.8.3 Công Thức Hybrid Đề Xuất

```text
FinalScore = AlphaBetaScore + lambda * confidence(s,a) * Q(s,a)
```

## 2.9 ELO Rating

### 2.9.1 Công Thức Expected Score

### 2.9.2 Công Thức Cập Nhật Rating

---

# Chương 3. Phân Tích Và Thiết Kế Hệ Thống

## 3.1 Kiến Trúc Tổng Quan

## 3.2 Luồng Xử Lý Chính

### 3.2.1 Luồng Train

### 3.2.2 Luồng Evaluate

### 3.2.3 Luồng Play/Demo

## 3.3 Module Board

### 3.3.1 `ChessEnv`

### 3.3.2 Sinh Nước Hợp Lệ

### 3.3.3 Reset, Copy, Push, Pop

## 3.4 Module State

### 3.4.1 Full State Key

### 3.4.2 Compact State Key

### 3.4.3 State Resolver

## 3.5 Module Evaluation

### 3.5.1 Material

### 3.5.2 Piece-Square Table

### 3.5.3 Mobility

### 3.5.4 King Safety

### 3.5.5 Center Control

### 3.5.6 Pawn Structure

### 3.5.7 Development

### 3.5.8 Threat/Hanging Piece

### 3.5.9 Check/Checkmate/Stalemate

## 3.6 Module Search

### 3.6.1 Minimax

### 3.6.2 Alpha-Beta

### 3.6.3 Move Ordering

### 3.6.4 Transposition Table

### 3.6.5 Quiescence Search

### 3.6.6 Iterative Deepening

## 3.7 Module Reinforcement Learning

### 3.7.1 QLearning

### 3.7.2 Reward Shaping

### 3.7.3 Replay Buffer

### 3.7.4 Batch Update

### 3.7.5 Quantized Q-Value

## 3.8 Module Agent

### 3.8.1 BaseAgent

### 3.8.2 MinimaxAgent

### 3.8.3 AlphaBetaAgent

### 3.8.4 HybridAgent

### 3.8.5 Explainable Score

## 3.9 Module Training

### 3.9.1 Self-play Game

### 3.9.2 Training Loop

### 3.9.3 Training History

## 3.10 Module Analytics

### 3.10.1 ELO

### 3.10.2 PGN Export

### 3.10.3 Plot Results

## 3.11 Module UI

### 3.11.1 Console UI

### 3.11.2 Pygame UI

### 3.11.3 Highlight Nước Hợp Lệ

### 3.11.4 Gợi Ý Nước Đi

### 3.11.5 Giải Thích Nước Đi

---

# Chương 4. Mô Hình Đề Xuất

## 4.1 Ba Mô Hình So Sánh

### 4.1.1 Model 1 - Minimax

### 4.1.2 Model 2 - Alpha-Beta

### 4.1.3 Model 3 - Hybrid

## 4.2 Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning

### 4.2.1 Động Cơ Đề Xuất

### 4.2.2 Công Thức Tổng Quát

### 4.2.3 Vai Trò Của Alpha-BetaScore

### 4.2.4 Vai Trò Của Q-Value

### 4.2.5 Vai Trò Của Confidence

### 4.2.6 Vai Trò Của Quantization

## 4.3 Reward Design

### 4.3.1 Terminal Reward

### 4.3.2 Shaping Reward

### 4.3.3 Move Reward

## 4.4 State Representation Design

### 4.4.1 Full FEN State

### 4.4.2 Compact State

### 4.4.3 So Sánh Full Và Compact

## 4.5 Explainable Recommendation

### 4.5.1 Các Thành Phần Giải Thích

| Thành phần | Ý nghĩa |
|---|---|
| AlphaBetaScore | Điểm tìm kiếm theo độ sâu |
| QValue | Kinh nghiệm học từ self-play |
| Confidence | Độ tin cậy dựa trên `N(s,a)` |
| QBonus | Phần cộng thêm từ Q-learning |
| FinalScore | Điểm cuối dùng để chọn nước |

### 4.5.2 Hiển Thị Trong UI

---

# Chương 5. Thực Nghiệm Và Đánh Giá

## 5.1 Môi Trường Thực Nghiệm

- Ngôn ngữ: Python
- Thư viện chính: `python-chess`, `pygame`, `matplotlib`, `pyyaml`, `pytest`
- Cấu hình máy chạy
- Số ván train/evaluate

## 5.2 Cấu Hình Tham Số

### 5.2.1 Search Config

### 5.2.2 Q-Learning Config

### 5.2.3 Hybrid Config

### 5.2.4 Evaluation Config

## 5.3 Kịch Bản Huấn Luyện

### 5.3.1 Full Q-Table

### 5.3.2 Compact Q-Table

### 5.3.3 Quantized Q-Table

## 5.4 Kịch Bản Đánh Giá

### 5.4.1 Round-Robin Tournament

### 5.4.2 Opening Robustness Benchmark

Danh sách khai cuộc:

- Start position
- Italian Game
- Sicilian Defense
- French Defense
- Queen's Gambit
- King's Indian

## 5.5 Metric Đánh Giá

### 5.5.1 Win/Loss/Draw

### 5.5.2 ELO

### 5.5.3 Avg Time Per Move

### 5.5.4 Nodes Visited

### 5.5.5 Nodes Pruned

### 5.5.6 Cache Hits

### 5.5.7 Q-Table Size

### 5.5.8 Unique States

### 5.5.9 Actions Per State

## 5.6 Kết Quả Huấn Luyện

### 5.6.1 Q-Table Growth

### 5.6.2 Epsilon Decay

### 5.6.3 Reward Theo Số Ván

### 5.6.4 Mean Absolute Q-Value

## 5.7 Kết Quả Đánh Giá Chính

### 5.7.1 Bảng ELO

| Model | ELO |
|---|---:|
| Hybrid Confidence + Quantized | 1561 |
| Alpha-Beta | 1560 |
| Minimax | 1379 |

### 5.7.2 Nhận Xét Kết Quả

- Hybrid vượt rõ Minimax.
- Hybrid xấp xỉ Alpha-Beta trong benchmark đa khai cuộc.
- Confidence-aware Q bonus giúp Q-value ảnh hưởng có kiểm soát.

## 5.8 Kết Quả Node/Pruning

### 5.8.1 Nodes Visited

### 5.8.2 Nodes Pruned

### 5.8.3 Cache Hits

## 5.9 Kết Quả Opening Robustness Benchmark

### 5.9.1 Theo Từng Khai Cuộc

### 5.9.2 Nhận Xét Tổng Quát

## 5.10 Ablation Study

### 5.10.1 Full vs Compact

### 5.10.2 Compact vs Quantized

### 5.10.3 Confidence Off vs Confidence On

### 5.10.4 Search Baseline vs Search Nâng Cấp

## 5.11 Demo Giao Diện

### 5.11.1 Console Demo

### 5.11.2 Pygame Demo

### 5.11.3 Explainable Move Demo

---

# Chương 6. Kiểm Thử

## 6.1 Chiến Lược Kiểm Thử

## 6.2 Unit Test

### 6.2.1 Test Board

### 6.2.2 Test Search

### 6.2.3 Test Q-Learning

### 6.2.4 Test Compact State

### 6.2.5 Test Transposition Table

### 6.2.6 Test Quiescence Search

### 6.2.7 Test PGN/ELO

### 6.2.8 Test Pygame Helpers

## 6.3 Kết Quả Test

```text
64 passed
```

## 6.4 Kiểm Tra Compile

```bash
python -m compileall -q src scripts
```

---

# Chương 7. Kết Luận Và Hướng Phát Triển

## 7.1 Kết Luận

- Đã xây dựng thành công ba mô hình.
- Hybrid Confidence + Quantized đạt kết quả tốt trong benchmark đa khai cuộc.
- Đồ án chứng minh hướng kết hợp Alpha-Beta và Q-learning có tiềm năng.

## 7.2 Hạn Chế

- Chưa dùng neural network.
- Q-learning vẫn là dạng bảng.
- Số ván train/evaluate còn giới hạn.
- Depth search còn thấp do giới hạn thời gian tính toán.
- Kết quả ELO chỉ mang tính nội bộ trong môi trường thực nghiệm của đồ án.

## 7.3 Hướng Phát Triển

- Deep Q-Network hoặc function approximation.
- Policy/value network.
- MCTS kết hợp neural network.
- Opening book.
- Endgame tablebase.
- Parallel search.
- UI nâng cấp đầy đủ hơn.

---

# Tài Liệu Tham Khảo

- Stuart Russell, Peter Norvig, Artificial Intelligence: A Modern Approach.
- Tài liệu `python-chess`.
- Tài liệu Minimax và Alpha-Beta Pruning.
- Tài liệu Q-learning và Reinforcement Learning.
- Tài liệu ELO rating.

---

# Phụ Lục A. Lệnh Chạy

## A.1 Cài Đặt

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## A.2 Train

```bash
python scripts/train.py --config config/config.yaml
```

## A.3 Train Quantized

```bash
python scripts/train.py --config config/config.yaml --games 500 --max-moves 80 --save-every 100 --state-representation compact --q-value-step 0.05 --q-value-clip 5.0 --q-table data/q_tables/q_quantized.pkl --history experiments/results/history_quantized.csv --seed 7
```

## A.4 Evaluate

```bash
python scripts/evaluate.py --config config/config.yaml --games 2 --depth 2 --max-moves 80 --q-table data/q_tables/q_quantized.pkl --state-representation compact --openings suite
```

## A.5 Play Console

```bash
python scripts/play.py --agent hybrid --depth 2 --q-table data/q_tables/q_table.pkl
```

## A.6 Play Pygame

```bash
python scripts/play.py --ui pygame --agent hybrid --depth 2 --q-table data/q_tables/q_table.pkl
```

## A.7 Test

```bash
python -m pytest -q
python -m compileall -q src scripts
```

---

# Phụ Lục B. Ánh Xạ Module

Tham khảo `docs/STRUCTURE.md`.

# Phụ Lục C. Phân Công Công Việc

Tham khảo `docs/TASK_ASSIGNMENT.md`.
