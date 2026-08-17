# Chess XAI Tutor

**Dùng thử ngay:** https://chess-xai-tutor.onrender.com

Bạn thua một ván cờ và muốn biết **mình sai ở đâu, vì sao sai, và lần sau nên làm gì**?

Stockfish trả lời rất giỏi câu "nước nào tốt nhất", nhưng chỉ đưa ra con số (-1.7, +0.4...) mà người mới không hiểu. Chess XAI Tutor phân tích ván cờ với độ chính xác của Stockfish rồi **giải thích bằng tiếng Việt tự nhiên**, cho bạn **xem đối thủ trừng phạt sai lầm của mình từng bước ngay trên bàn cờ**, và **luyện lại đúng chỗ bạn hay sai**.

> *"h3 là sai lầm nghiêm trọng; nước tốt hơn là Kf2. Cơ hội thắng giảm từ 84% xuống 51%. Nước này mở đường cho đối thủ tạo đòn đôi. Đối thủ có thể trừng phạt bằng: 1...Nc2+ 2. Kd2 Nxa1."*
> — một câu giải thích thật do phần mềm sinh ra

Không dùng mô hình ngôn ngữ để "bịa" lý do: mọi câu giải thích sinh từ bằng chứng kiểm chứng được — điểm số engine, luật cờ, và phân rã hàm đánh giá.

## Bạn làm được gì

**Nhập tên là xong.** Gõ tên Chess.com hoặc Lichess của bạn, chọn số ván → phần mềm tự kéo các ván bạn đã chơi về và phân tích hết. Không cần biết PGN là gì. (Vẫn có ô dán PGN cho ván bất kỳ.)

**Xem lại ván như có huấn luyện viên ngồi cạnh.** Danh sách nước tô màu theo chất lượng, thanh ưu thế đen–trắng, mỗi nước một dòng lý do chính bằng tiếng Việt. Với nước sai: mũi tên chỉ nước nên đi, nút **"Xem đòn trừng phạt"** phát lại biến từng bước có chú thích *("đòn đôi: mã c2 tấn công cùng lúc xe a1 và vua e1", "ăn xe (5 điểm)")*, nút **"Xem nước đúng"** cho biến nên đi. Xoay bàn cờ khi bạn cầm Đen.

**Hồ sơ điểm yếu cá nhân.** Gộp nhiều ván, chỉ tính nước của bạn: chính xác bao nhiêu và đang lên hay xuống, sai nhiều ở khai / trung / tàn cuộc, hay để hở đòn gì (đòn đôi, ghim, đòn xiên, đòn mở), khai cuộc nào chơi tệ và thường sai từ nước mấy, những nước tệ nhất (bấm là mở lại).

**Bài tập sinh từ chính lỗi của bạn.** Mỗi sai lầm có đòn trừng phạt trở thành một bài "tìm đòn trừng phạt" trên bàn cờ. Đúng thì giãn lịch ôn (1 → 3 → 7 → 14 → 30 ngày), sai thì ôn lại hôm sau — cách học đã được chứng minh hiệu quả. Bài từ lỗi của bạn dạy bạn thấy đòn mình để hở; bài từ lỗi của đối thủ dạy bạn không bỏ lỡ cơ hội.

**Chơi với AI có giải thích trực tiếp** (bản chạy trên máy): ba mức độ khó, sau mỗi nước có câu giải thích, phím `H` gợi ý kèm biến chính, phím `T` tổng kết ván.

## Chạy trên máy của bạn

Bản web công khai chạy trên máy chủ miễn phí nên chậm hơn và ngủ khi không ai dùng. Chạy trên máy bạn thì nhanh gấp nhiều lần và giữ dữ liệu lâu dài:

```bash
git clone https://github.com/MinhNhat-2504/chess-xai-tutor.git
cd chess-xai-tutor
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

**Cài Stockfish (khuyến nghị mạnh):** tải miễn phí tại [stockfishchess.org/download](https://stockfishchess.org/download/), rồi làm một trong ba cách — phần mềm tự dò theo thứ tự này:

1. Đặt biến môi trường `STOCKFISH_PATH` trỏ tới file thực thi;
2. Thêm Stockfish vào `PATH`;
3. Chép engine vào `engines/stockfish/stockfish.exe` trong thư mục dự án.

Không có Stockfish phần mềm vẫn chạy bằng engine Alpha-Beta tự viết, nhưng kết luận kém tin cậy hơn.

**Mở web:** bấm đúp `start_web.bat` (Windows), hoặc:

```bash
python scripts/web_app.py
```

Mở địa chỉ nó in ra (mặc định `http://127.0.0.1:8000`; nếu cổng bị Windows chặn, script tự chọn cổng khác). Các lệnh khác:

```bash
python scripts/play.py --ui pygame                 # chơi với AI, có giải thích trực tiếp
python scripts/xai_viewer.py                       # viewer PGN kiểu Pygame
python scripts/analyze_game.py van-co.pgn --output bao_cao.json   # xuất báo cáo JSON
```

Chế độ mặc định phân tích một ván 140 nửa nước trong ~50 giây (depth 12; đo thực tế cho kết luận ngang depth 14 mà nhanh gấp 3). Trên web chọn "Kỹ" (depth 16) cho ván quan trọng. Cấu hình ở mục `xai` trong [config/config.yaml](config/config.yaml).

**Đưa lên web công khai:** repo có sẵn `Dockerfile` và `render.yaml` — xem [docs/DEPLOY.md](docs/DEPLOY.md) (Render miễn phí, hoặc VPS bất kỳ chạy Docker).

## Phần mềm hoạt động thế nào?

Mỗi báo cáo nước đi ghép từ bốn nguồn bằng chứng độc lập:

| Nguồn | Trả lời câu hỏi | Lấy từ |
|---|---|---|
| Counterfactual | Nước nào tốt hơn? Kém bao nhiêu? | Stockfish (MultiPV) hoặc Alpha-Beta nội bộ |
| Đòn trừng phạt | Vì sao nước này sai? | Biến chính (PV) của engine, chú thích từng bước |
| Motif chiến thuật | Đòn này tên là gì? | Luật cờ thuần (`src/xai/motifs.py`): đòn đôi, ghim, đòn xiên, đòn mở, chiếu hết tầng cuối |
| Attribution | Thế trận thay đổi ra sao? | Hàm đánh giá 8 thành phần (vật chất, an toàn vua, trung tâm...) |

Câu tiếng Việt sinh bằng template từ các bằng chứng trên — trung thực, tái lập được; trường `method` trong mỗi báo cáo ghi rõ engine và độ sâu đã dùng. Chi tiết: [docs/XAI.md](docs/XAI.md).

## Cấu trúc dự án

```text
src/
  xai/          # Trái tim của dự án
    explainer.py      # giải thích một nước đi (điểm số, lý do, đòn trừng phạt)
    engine_oracle.py  # Stockfish: cache theo thế cờ, nắp thời gian, MultiPV
    motifs.py         # nhận diện đòn đôi / ghim / đòn xiên / đòn mở / chiếu tầng cuối
    game_summary.py   # tổng kết ván: accuracy, ACPL, lỗi theo giai đoạn
    game_import.py    # kéo ván từ Chess.com / Lichess (API công khai)
    profile.py        # hồ sơ điểm yếu nhiều ván
    store.py          # SQLite: ván đã phân tích, bài tập, lịch ôn ngắt quãng
  ui/           # web (Flask), màn chơi Pygame, viewer PGN
  agents/, search/, evaluation/, rl/, training/   # engine tự viết & phần nghiên cứu gốc
scripts/        # web_app.py, play.py, xai_viewer.py, analyze_game.py, train/evaluate/benchmark
```

Kiểm thử (117 test, tự bỏ qua các test cần Stockfish nếu máy chưa cài):

```bash
python -m pytest -q
```

## Nguồn gốc dự án

Phát triển từ đồ án môn **Nhập môn Trí tuệ nhân tạo** — Khoa CNTT, Trường ĐH Văn Lang (Nhóm 9), GVHD: ThS. Phan Hồ Viết Trường.

Phần nghiên cứu gốc xây dựng và so sánh ba engine: Minimax, Alpha-Beta, và biến thể **Confidence-Aware Quantized Hybrid Alpha-Beta Q-Learning** (điểm Alpha-Beta cộng Q-value học từ self-play, có trọng số tin cậy `N/(N+k)`), kèm benchmark 900 ván trên 6 khai cuộc cho hệ 3 mức độ khó (ELO ~1096 / 1648 / 1756). Chi tiết trong [docs/](docs/README.md): [XAI.md](docs/XAI.md), [PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md), [CONG_THUC.md](docs/CONG_THUC.md), [NOVELTY_CONTRIBUTION.md](docs/NOVELTY_CONTRIBUTION.md).

Stockfish và python-chess theo giấy phép GPLv3; dự án dùng chúng dưới dạng dịch vụ web và giữ mã nguồn mở.

## Hướng phát triển

- Bàn cờ kéo-thả và giao diện điện thoại tốt hơn.
- Bảng điều khiển cho huấn luyện viên / CLB: theo dõi nhiều học viên, giao bài tập tự động.
- Thêm motif nâng cao: quá tải, đánh lạc hướng, chiếu đôi.
- Nút bật/tắt giao diện tối / sáng.
