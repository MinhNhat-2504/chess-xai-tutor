# Tài Liệu Đồ Án

Thư mục này gom tài liệu kỹ thuật, công thức và phần trình bày novelty để đưa vào báo cáo.

## Tài Liệu Chính

| File | Nội dung | Khi dùng |
|---|---|---|
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | Tổng hợp toàn bộ đồ án trong một file | Khi cần đọc nhanh hoặc gửi kèm báo cáo |
| [STRUCTURE.md](STRUCTURE.md) | Ánh xạ file/module với mục báo cáo | Khi giải thích kiến trúc repo |
| [TASK_ASSIGNMENT.md](TASK_ASSIGNMENT.md) | Rule, skill, task, phân công thành viên | Khi chia việc hoặc nghiệm thu module |
| [REPORT_OUTLINE.md](REPORT_OUTLINE.md) | Outline đầy đủ để cập nhật file Word báo cáo | Khi dựng mục lục và đề mục Word |
| [CONG_THUC.md](CONG_THUC.md) | Công thức đánh giá, Minimax, Alpha-Beta, Q-learning, Hybrid | Khi viết chương cơ sở lý thuyết |
| [NOVELTY_CONTRIBUTION.md](NOVELTY_CONTRIBUTION.md) | Research gap, novelty, contribution, cách nói khi bảo vệ | Khi viết mở đầu/kết luận |
| [architecture/architecture.pdf](architecture/architecture.pdf) | Sơ đồ kiến trúc và luồng xử lý | Khi đưa hình vào báo cáo |

## Luồng Báo Cáo Gợi Ý

1. **Mục tiêu đề tài**: so sánh Minimax, Alpha-Beta và Hybrid Q-learning.
2. **Cơ sở lý thuyết**: lấy công thức từ [CONG_THUC.md](CONG_THUC.md).
3. **Thiết kế hệ thống**: dùng [STRUCTURE.md](STRUCTURE.md) và sơ đồ architecture.
4. **Novelty**: trình bày Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning.
5. **Thực nghiệm**: dùng ELO, node visited/pruned, opening benchmark, benchmark 3 độ khó và training curves.
6. **Demo**: Pygame UI, chọn độ khó, quân cờ dạng shape, animation, âm thanh, gợi ý nước đi và explainable score.

## Novelty Tóm Tắt

Đồ án đề xuất biến thể:

```text
Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning
```

Công thức:

```text
FinalScore = AlphaBetaScore + lambda * confidence(s,a) * Q(s,a)
confidence(s,a) = N(s,a) / (N(s,a) + k)
```

Điểm mới nằm ở:

- Compact state representation để giảm state explosion.
- Quantized Q-value để kiểm tra tác động của lượng tử hoá.
- Confidence-aware Q bonus để tránh tin quá mạnh vào Q-value ít dữ liệu.
- MCTS root bonus cho preset Siêu khó địa ngục.
- Opening robustness benchmark để đánh giá trên nhiều khai cuộc.
- Explainable recommendation để giải thích nước đi trong UI/demo.

## Kết Quả Có Thể Trích Dẫn

Benchmark 3 mức độ khó theo yêu cầu GVHD, chạy 5 seeds (`7, 11, 13, 17, 19`), 6 khai cuộc, tổng 900 ván. Q-table dùng compact state + quantized Q-value; preset Hell tuned dùng Alpha-Beta depth 4, iterative deepening và MCTS root bonus.

| Chế độ | ELO mean±std | Score rate | Time/move | Nodes/move |
|---|---:|---:|---:|---:|
| Dễ | 1096.4±2.5 | 0.000 | 0.007s | 0 |
| Trung bình | 1648.1±24.9 | 0.664±0.030 | 0.904s | 817 |
| Siêu khó địa ngục | 1755.6±25.1 | 0.836±0.030 | 4.185s | 3753 |

Đối đầu trực tiếp:

| Cặp đấu | Kết quả |
|---|---|
| Dễ vs Trung bình | Trung bình thắng 300/300 |
| Dễ vs Siêu khó địa ngục | Siêu khó địa ngục thắng 300/300 |
| Siêu khó địa ngục vs Trung bình | Hell thắng 115, Trung bình thắng 12, hòa 173 |

Đoạn nhận xét ngắn:

> Benchmark 5 seeds cho thấy hệ thống phân cấp độ khó hoạt động rõ ràng: Easy gần như thua tuyệt đối trước hai mức còn lại, Medium tạo thử thách ổn định bằng Alpha-Beta, còn Hell đạt ELO cao nhất nhờ kết hợp Alpha-Beta depth lớn hơn, iterative deepening, compact quantized Q-learning và MCTS root bonus. Đổi lại, Hell có thời gian suy luận mỗi nước cao hơn, phù hợp với mục tiêu "Siêu khó địa ngục".
