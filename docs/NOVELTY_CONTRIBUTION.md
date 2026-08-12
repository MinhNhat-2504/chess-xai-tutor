# Novelty và Contribution của đồ án

Tài liệu này dùng để đưa vào phần **Mở đầu**, **Đóng góp của đề tài** và
**Kết luận** trong báo cáo. Cách diễn đạt nên trung thực: đồ án không tuyên bố
phát minh thuật toán cờ vua mới ở mức hàn lâm, mà đề xuất và kiểm chứng một
biến thể tích hợp trong phạm vi đồ án.

## 1. Research gap

Cờ vua có không gian trạng thái và hành động rất lớn. Q-learning dạng bảng
gặp vấn đề **state-action explosion**: nếu dùng FEN rút gọn làm state key, nhiều
trạng thái chỉ xuất hiện một lần trong self-play, khiến Q-table phình nhanh
nhưng kinh nghiệm khó được tái sử dụng.

Research gap của đồ án:

> Chưa rõ việc rút gọn và lượng tử hoá biểu diễn Q-learning có thể giảm độ phân
> mảnh của Q-table mà vẫn giữ được hiệu quả chọn nước trong mô hình Hybrid
> Alpha-Beta hay không.

Vì vậy đồ án kiểm tra ba hướng:

| Biến thể | State key | Q-value | Mục đích |
|---|---|---|---|
| Full Q | FEN rút gọn | Float | Baseline Q-table |
| Compact Q | Bucket `feature_vector` | Float | Giảm state explosion |
| Quantized Q | Compact state | Clip + làm tròn Q-value | Kiểm tra giảm nhiễu/kích thước giá trị Q |

## 2. Novelty

### 2.1 Novelty chính

Đồ án đề xuất biến thể:

> **Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning**

Biến thể này kết hợp:

- Alpha-Beta search để đánh giá chiến thuật theo độ sâu.
- Q-learning self-play để lưu kinh nghiệm theo cặp `(state, action)`.
- Compact state representation để gom các trạng thái tương tự.
- Quantized Q-value để kiểm tra tác động của việc clip/làm tròn Q-value.
- Confidence-aware Q bonus để Q-value chỉ ảnh hưởng mạnh khi cặp `(state, action)`
  đã được cập nhật đủ nhiều.

Công thức chọn nước của Hybrid:

```text
FinalScore(s, a) = AlphaBetaScore(s, a) + lambda * confidence(s,a) * Q(s, a)
```

Trong đó:

```text
confidence(s,a) = N(s,a) / (N(s,a) + k)
```

`N(s,a)` là số lần Q-table cập nhật cặp `(state, action)`, `k` là hệ số làm mượt.
Nếu tắt confidence-aware mode thì `confidence = 1`.

Trong biến thể quantized, Q-value sau Bellman update được chuẩn hoá:

```text
Q_raw   = Q(s,a) + alpha * [r + gamma * max Q(s',a') - Q(s,a)]
Q_clip  = clip(Q_raw, -C, C)
Q_quant = step * round(Q_clip / step)
```

Nếu không bật `q_value_step` và `q_value_clip`, hệ thống giữ nguyên hành vi
Q-learning float ban đầu.

### 2.2 Novelty phụ

Ngoài biến thể Q-learning, đồ án còn tích hợp các kỹ thuật nâng cấp:

- Transposition table với bound flag `EXACT / LOWER / UPPER`.
- Quiescence search để giảm horizon effect.
- Killer move và history heuristic cho move ordering.
- Mini-batch replay update từ `ReplayBuffer`.
- ELO rating, PGN export và biểu đồ thực nghiệm.
- Opening robustness benchmark trên nhiều khai cuộc.
- Explainable move recommendation: hiển thị `AlphaBetaScore`, `QValue`,
  `confidence`, `Q bonus`, `FinalScore`.
- Pygame UI có highlight nước hợp lệ và gợi ý nước đi.

## 3. Contribution

### 3.1 Contribution về mô hình

- Xây dựng ba mô hình so sánh trực tiếp: Minimax, Alpha-Beta và Hybrid.
- Giữ Minimax làm baseline để đảm bảo so sánh công bằng.
- Đề xuất Hybrid dùng `AlphaBetaScore + lambda * QValue`.
- Mở rộng Hybrid bằng compact state và quantized Q-value để kiểm tra research gap.
- Mở rộng thành Confidence-Aware Hybrid để giảm rủi ro Q-value nhiễu ở các
  state/action ít được học.

### 3.2 Contribution về huấn luyện

- Xây dựng vòng self-play sinh transition `(s, a, r, s', actions')`.
- Thiết kế reward gồm terminal reward, shaping reward và move reward.
- Dùng replay buffer và mini-batch update để tái sử dụng kinh nghiệm.
- Ghi history gồm `q_size`, `unique_states`, `actions_per_state`, `mean_abs_q`,
  `epsilon`, `reward` để phân tích quá trình học.

### 3.3 Contribution về tìm kiếm

- Cài đặt Alpha-Beta có thống kê `visited`, `pruned`, `cache_hits`.
- Bổ sung move ordering theo MVV-LVA, killer move và history heuristic.
- Bổ sung transposition table an toàn bằng bound flag.
- Bổ sung quiescence search và iterative deepening để nâng chất lượng tìm kiếm.

### 3.4 Contribution về thực nghiệm

- Tự động đánh giá round-robin giữa các mô hình.
- Xuất CSV/JSON/PGN để kiểm tra lại ván đấu và thống kê.
- Tính ELO tuần tự cho từng model.
- Sinh biểu đồ training/evaluation phục vụ báo cáo.
- Có thể chạy ablation giữa `full`, `compact`, `quantized`.
- Có thể chạy benchmark đa khai cuộc bằng `--openings suite`.

### 3.5 Contribution về demo

- Có console UI để nhập nước bằng UCI/SAN.
- Có Pygame UI để chơi trực quan.
- UI hỗ trợ highlight nước hợp lệ và gợi ý nước đi bằng agent.
- UI/console hiển thị giải thích nước đi cho Hybrid: điểm Alpha-Beta, Q-value,
  confidence và final score.

## 4. Evidence từ kết quả hiện tại

Kết quả evaluate với Quantized Q-table:

| Model | ELO |
|---|---:|
| Alpha-Beta | 1565 |
| Hybrid Quantized | 1557 |
| Minimax | 1378 |

Nhận xét:

- Hybrid Quantized vượt Minimax rõ rệt.
- Hybrid Quantized chỉ kém Alpha-Beta khoảng 8 ELO trong thí nghiệm hiện tại.
- Điều này cho thấy compact state + quantized Q-value không làm mô hình mất sức
  chơi đáng kể, đồng thời tạo cơ sở để bàn về hướng giảm state-action explosion.

## 5. Cách viết ngắn trong báo cáo

Có thể dùng đoạn sau:

> Đóng góp chính của đồ án là xây dựng và kiểm chứng một mô hình Chess AI lai,
> kết hợp Alpha-Beta search với Q-learning tự cải thiện qua self-play. Bên cạnh
> baseline Minimax và Alpha-Beta, đồ án đề xuất biến thể Confidence-Aware
> Quantized Hybrid Alpha-Beta Q-Learning, trong đó trạng thái Q-learning được
> rút gọn bằng compact feature binning, Q-value được clip/lượng tử hoá và ảnh
> hưởng của Q-value được điều chỉnh theo độ tin cậy dựa trên số lần học. Biến
> thể này nhằm kiểm tra research gap state-action explosion của Q-learning dạng
> bảng trong cờ vua.

## 6. Cách nói khi bảo vệ

Nên nói:

- "Đồ án đề xuất biến thể tích hợp trong phạm vi ứng dụng."
- "Novelty nằm ở cách kết hợp, lượng tử hoá và đánh giá thực nghiệm."
- "Không tuyên bố đây là thuật toán cờ vua state-of-the-art."

Không nên nói:

- "Đây là thuật toán cờ vua hoàn toàn mới."
- "Mô hình đã vượt Alpha-Beta tuyệt đối."
- "Q-learning đã giải quyết hoàn toàn state explosion."
