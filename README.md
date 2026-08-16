---
title: Chess XAI Tutor
emoji: ♟️
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Chess XAI Tutor — Phân tích ván cờ và giải thích bằng tiếng Việt

Bạn thua một ván cờ và muốn biết **mình sai ở đâu, vì sao sai, và lần sau nên làm gì**?

Các công cụ như Stockfish trả lời rất giỏi câu "nước nào tốt nhất", nhưng chỉ đưa ra con số (-1.7, +0.4...) mà người mới nhìn vào không hiểu gì. Dự án này lấp khoảng trống đó: **phân tích ván cờ với độ chính xác của Stockfish, rồi giải thích bằng tiếng Việt tự nhiên** — nước này là đòn đôi, nước kia để hở ghim, blunder này sẽ bị trừng phạt bằng biến nào.

> *"h3 là sai lầm nghiêm trọng (blunder); nước tốt hơn là Kf2. Cơ hội thắng giảm từ 84% xuống 51%. Nước này mở đường cho đối thủ tạo đòn đôi (fork). Đối thủ có thể trừng phạt bằng: 1...Nc2+ 2. Kd2 Nxa1."*
> — một câu giải thích thật do phần mềm sinh ra

Điểm khác biệt: **không dùng mô hình ngôn ngữ để "bịa" lý do**. Mọi câu giải thích đều sinh từ bằng chứng kiểm chứng được — điểm số engine, luật cờ, và phân rã hàm đánh giá.

## Tính năng chính

**Phân tích từng nước đi**
- Điểm số, nước tốt nhất, top phương án và biến chính lấy từ **Stockfish** (tự rơi về engine nội bộ nếu máy chưa cài).
- Nhãn chất lượng quen thuộc: nước tốt nhất / nước tốt / thiếu chính xác / sai lầm / blunder.
- **Đòn trừng phạt**: với nước sai, hiện luôn chuỗi nước đối thủ khai thác — trả lời câu "vì sao sai".
- **Cơ hội thắng** (%) quy đổi theo công thức Lichess.

**Motif chiến thuật có tên** — ngôn ngữ mà người học cờ thực sự dùng:
- Đòn đôi (fork), ghim (pin), đòn xiên (skewer), đòn mở (discovered attack/check), chiếu hết tầng cuối.
- Với nước sai, phần mềm soi cả motif mà nước đó *cho phép đối thủ* thực hiện.

**Chơi với AI và học ngay trong ván**
- Ba mức độ khó: Dễ (người mới cũng thắng được), Trung bình, Siêu khó địa ngục.
- Sau mỗi nước đi, câu giải thích hiện ngay dưới bàn cờ.
- Phím `H`: gợi ý nước tốt nhất kèm biến chính. Phím `T`: tổng kết ván.

**Tổng kết ván để rút kinh nghiệm**
- Accuracy và ACPL từng bên — hai chỉ số chuẩn để đo trình độ.
- Lỗi phân theo giai đoạn khai cuộc / trung cuộc / tàn cuộc.
- Danh sách nước cần xem lại và **chủ đề cần luyện** (bạn hay để hở đòn gì).

**Xem lại ván đấu từ Chess.com / Lichess**
- **Giao diện web**: dán PGN hoặc chọn file là có ngay bảng phân tích trên trình duyệt — bàn cờ, danh sách nước tô màu theo chất lượng, giải thích từng nước và tổng kết ván.
- **Học từ nước sai, không chỉ biết mình sai**: với mỗi sai lầm, bấm "Xem đối thủ trừng phạt thế nào" để phát lại đòn từng bước ngay trên bàn cờ, có mũi tên và chú thích ("đòn đôi: mã c2 tấn công cùng lúc xe a1 và vua e1", "ăn xe (5 điểm)"). Tập tự đoán nước kế tiếp trước khi bấm — đó là cách luyện mắt nhìn chiến thuật.
- Hoặc viewer Pygame: kéo-thả file PGN, bấm "Lỗi kế" để nhảy thẳng tới các nước sai.

## Cài đặt

```bash
git clone https://github.com/MinhNhat-2504/chess-xai-tutor.git
cd chess-xai-tutor
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

**Cài Stockfish (khuyến nghị mạnh):** tải bản miễn phí tại [stockfishchess.org/download](https://stockfishchess.org/download/), sau đó chọn một trong ba cách — phần mềm tự dò theo thứ tự này:

1. Đặt biến môi trường `STOCKFISH_PATH` trỏ tới file thực thi;
2. Thêm Stockfish vào `PATH`;
3. Chép engine vào `engines/stockfish/stockfish.exe` trong thư mục dự án.

Không có Stockfish phần mềm vẫn chạy đầy đủ tính năng bằng engine Alpha-Beta tự viết, nhưng kết luận chất lượng nước đi sẽ kém tin cậy hơn.

## Dùng thử trong 30 giây

**Phân tích ván cờ trên trình duyệt** — cách dễ nhất:

```bash
python scripts/web_app.py
```

Mở `http://127.0.0.1:8000`, dán PGN từ Chess.com (vào ván đấu → Share → tab PGN → copy) hoặc chọn file `.pgn`, bấm "Phân tích ván cờ". Kết quả hiện dần từng nước, không phải chờ cả ván.

**Chơi với AI, có giải thích trực tiếp:**

```bash
python scripts/play.py --ui pygame
```

**Xem lại PGN bằng viewer Pygame** (kéo-thả file vào cửa sổ):

```bash
python scripts/xai_viewer.py
```

**Xuất báo cáo phân tích ra JSON:**

```bash
python scripts/analyze_game.py duong-dan/van-co.pgn --output bao_cao.json
```

Tuỳ chọn hay dùng: `--engine-depth 18` (phân tích kỹ hơn), `--no-stockfish` (chỉ dùng engine nội bộ). Cấu hình mặc định nằm ở mục `xai` trong [config/config.yaml](config/config.yaml). Chi tiết đầy đủ: [docs/XAI.md](docs/XAI.md).

**Đưa lên web công khai (miễn phí):** repo có sẵn `Dockerfile`; xem [docs/DEPLOY.md](docs/DEPLOY.md) để deploy lên Hugging Face Spaces / Render trong vài phút.

## Phần mềm hoạt động thế nào?

Mỗi báo cáo nước đi ghép từ bốn nguồn bằng chứng độc lập:

| Nguồn | Trả lời câu hỏi | Lấy từ |
|---|---|---|
| Counterfactual | Nước nào tốt hơn? Kém bao nhiêu? | Stockfish (MultiPV) hoặc Alpha-Beta nội bộ |
| Đòn trừng phạt | Vì sao nước này sai? | Biến chính (PV) của engine |
| Motif chiến thuật | Đòn này tên là gì? | Luật cờ thuần (`src/xai/motifs.py`) |
| Attribution | Thế trận thay đổi ra sao? | Hàm đánh giá 8 thành phần (vật chất, an toàn vua, trung tâm...) |

Câu tiếng Việt được sinh bằng template từ các bằng chứng trên — trung thực, tái lập được, và trường `method` trong mỗi báo cáo ghi rõ engine + độ sâu đã dùng.

## Cấu trúc dự án

```text
src/
  xai/          # Trái tim của dự án: explainer, Stockfish oracle, motif, tổng kết ván
  agents/       # MinimaxAgent, AlphaBetaAgent, HybridAgent, 3 mức độ khó
  search/       # Alpha-Beta, transposition table, quiescence, MCTS
  evaluation/   # Hàm đánh giá 8 thành phần
  rl/           # Q-Learning, replay buffer (phần nghiên cứu của đồ án)
  training/     # Self-play training
  ui/           # Web UI, màn chơi Pygame, viewer phân tích PGN
scripts/
  web_app.py        # Giao diện web: dán/upload PGN, phân tích trên trình duyệt
  play.py           # Chơi với AI (console hoặc pygame)
  xai_viewer.py     # Viewer phân tích PGN (Pygame)
  analyze_game.py   # Phân tích PGN ra JSON
  train.py, evaluate.py, benchmark_difficulty.py   # Phục vụ nghiên cứu
```

Kiểm thử (106 test, tự bỏ qua các test cần Stockfish nếu máy chưa cài):

```bash
python -m pytest -q
```

## Nguồn gốc dự án

Dự án phát triển từ đồ án môn **Nhập môn Trí tuệ nhân tạo** — Khoa CNTT, Trường ĐH Văn Lang (Nhóm 9), GVHD: ThS. Phan Hồ Viết Trường.

Phần nghiên cứu gốc xây dựng và so sánh ba engine: Minimax, Alpha-Beta, và biến thể **Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning** (điểm Alpha-Beta cộng Q-value học từ self-play, có trọng số tin cậy `N/(N+k)`), kèm benchmark 900 ván trên 6 khai cuộc cho hệ 3 mức độ khó (ELO ~1096 / 1648 / 1756). Chi tiết trong [docs/](docs/README.md):

| Tài liệu | Nội dung |
|---|---|
| [docs/XAI.md](docs/XAI.md) | Lớp giải thích nước đi (phần chính của phần mềm) |
| [docs/PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md) | Tổng hợp đồ án gốc |
| [docs/CONG_THUC.md](docs/CONG_THUC.md) | Công thức Minimax, Alpha-Beta, Q-learning, Hybrid |
| [docs/NOVELTY_CONTRIBUTION.md](docs/NOVELTY_CONTRIBUTION.md) | Research gap và đóng góp |

## Hướng phát triển

- Bấm vào một phương án bất kỳ (không chỉ nước sai) để xem biến thể diễn ra trên bàn cờ.
- Lưu lịch sử nhiều ván để theo dõi tiến bộ (accuracy tăng, motif để hở giảm).
- Thêm motif nâng cao: quá tải (overloading), đánh lạc hướng (deflection), chiếu đôi.
- Lưu lịch sử người dùng, đăng nhập, gói trả phí — nếu phát triển thành dịch vụ.
