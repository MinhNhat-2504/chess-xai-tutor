# XAI: giải thích nước đi để tự học cờ

Module `src/xai` giải thích một nước đi bằng bằng chứng sinh trực tiếp từ
engine, thay vì chỉ hiện các con số Alpha-Beta/Q-value.

Từ phiên bản này, **điểm số, nước tốt nhất, top phương án (MultiPV) và biến
chính (PV) lấy từ Stockfish** khi máy có engine — chuẩn như các trang phân tích
Chess.com/Lichess. Phần *diễn giải* (phân rã 8 thành phần, sự kiện chiến thuật,
câu tiếng Việt) vẫn do project tự sinh, không dùng mô hình ngôn ngữ để bịa lý
do. Khi không tìm thấy Stockfish, hệ thống tự rơi về Alpha-Beta + evaluator nội
bộ như trước.

## Cài đặt Stockfish

Tải bản Windows từ <https://stockfishchess.org/download/> (hoặc GitHub
`official-stockfish/Stockfish`), rồi làm một trong ba cách — hệ thống dò theo
thứ tự này:

1. Đặt biến môi trường `STOCKFISH_PATH` trỏ tới file `.exe`.
2. Thêm thư mục chứa `stockfish.exe` vào `PATH`.
3. Chép engine vào `engines/stockfish/stockfish.exe` trong repo (thư mục
   `engines/` đã nằm trong `.gitignore`, không bị commit).

Cấu hình mặc định nằm ở mục `xai` trong `config/config.yaml` (`engine_depth`,
`multipv`, `use_stockfish`).

## Ứng dụng đồ hoạ cho người học

Mở ứng dụng bằng lệnh sau:

```bash
python scripts/xai_viewer.py                 # tự dò Stockfish, depth 14
python scripts/xai_viewer.py --no-stockfish --depth 2   # chỉ dùng engine nội bộ
```

Trong cửa sổ, bấm **Chọn file PGN** hoặc kéo-thả file `.pgn` đã tải từ
Chess.com/Lichess. Ứng dụng phân tích ngầm để cửa sổ không bị treo; dùng
**Lỗi kế** (hoặc phím `N`/Space) để nhảy tới nước thiếu chính xác, sai lầm hay
blunder. Mỗi nước hiển thị bàn cờ, nước tốt hơn, mức thiệt hại, cơ hội thắng,
đòn trừng phạt của đối thủ (với nước sai), các yếu tố cờ thay đổi và lời giải
thích tiếng Việt. Engine đang dùng hiển thị ngay trên panel.

Mỗi báo cáo gồm:

- **Counterfactual**: nước tốt nhất, top phương án kèm biến chính, điểm của
  nước đã đi và `centipawn_loss` (từ Stockfish khi có oracle).
- **Nhãn học tập**: `best`, `good`, `inaccuracy`, `mistake`, hoặc `blunder`.
- **Đòn trừng phạt** (`refutation_san`): chuỗi nước đối thủ đáp trả tốt nhất
  sau nước đã đi — trả lời câu hỏi "vì sao nước này sai".
- **Motif chiến thuật có tên** (`motifs`): đòn đôi (fork), ghim (pin), đòn xiên
  (skewer), đòn mở (discovered attack/check), chiếu hết tầng cuối — phát hiện
  bằng luật cờ thuần trong `src/xai/motifs.py`, hoạt động cả khi không có
  Stockfish. Với nước sai, trường `opponent_motifs` soi cả motif mà nước đó
  *cho phép đối thủ* thực hiện trong biến trừng phạt (ví dụ: "Nước này mở đường
  cho đối thủ tạo đòn đôi").
- **Cơ hội thắng** (`win_chance`): quy đổi centipawn theo công thức Lichess.
- **Attribution**: so sánh trước/sau theo vật chất-vị trí, cơ động, an toàn vua,
  trung tâm, cấu trúc tốt, phát triển quân, quân treo và sức ép chiếu.
- **Sự kiện luật cờ**: bắt quân, chiếu/chiếu hết, nhập thành, phong cấp và quân
  treo. Những sự kiện này giúp người học biết *vì sao* nước đó đáng chú ý.

## Giao diện web: dán PGN là có phân tích

```bash
python scripts/web_app.py
```

Mở trình duyệt tại `http://127.0.0.1:8000`, dán PGN (Chess.com: vào ván đấu →
Share → tab PGN → copy) hoặc chọn file `.pgn`, bấm **Phân tích ván cờ**. Kết
quả hiện dần từng nước trong lúc phân tích chạy nền: bàn cờ SVG, danh sách
nước tô màu theo chất lượng, câu giải thích tiếng Việt, đòn trừng phạt, top
phương án kèm biến chính, và thẻ tổng kết ván khi xong. Điều hướng bằng phím
`←`/`→`, nút "Lỗi kế" nhảy tới nước sai tiếp theo.

Trang web tự chứa (không cần internet), chỉ chạy trên máy bạn (`127.0.0.1`).
Tuỳ chọn: `--port`, `--engine-depth`, `--no-stockfish`.

## Giải thích trực tiếp khi chơi với AI

```bash
python scripts/play.py --ui pygame
```

Khi mục `xai.live_explanations` trong config bật (mặc định), màn chơi Pygame có
một worker phân tích ngầm: sau mỗi nước (của bạn lẫn AI), câu giải thích tiếng
Việt kèm nhãn chất lượng hiện ngay dưới bàn cờ. Phím tắt:

- **H** — gợi ý nước tốt nhất từ Stockfish, kèm cơ hội thắng và biến chính.
- **T** — bật/tắt trang tổng kết ván (xem mục dưới); cuối ván ứng dụng tự nhắc.

## Tổng kết ván để rút kinh nghiệm

`src/xai/game_summary.py` gộp các báo cáo từng nước thành tổng kết:

- **Accuracy** mỗi bên (công thức Lichess, quy đổi từ mức sụt cơ hội thắng) và
  **ACPL** (average centipawn loss).
- **Số lỗi theo giai đoạn** khai cuộc / trung cuộc / tàn cuộc (giai đoạn xác
  định bằng vật chất còn lại và số nước đã đi) — chỉ ra bạn yếu ở đâu.
- **Nước cần xem lại**: các nước tệ nhất kèm số nước và mức thiệt hại.
- **Chủ đề cần luyện**: thống kê motif bạn để đối thủ tạo ra (ví dụ "để hở đòn
  đôi ×2").

Trang tổng kết có ở cả hai nơi: màn chơi trực tiếp (phím **T**) và viewer PGN
(nút **Tổng kết** hoặc phím **T**).

## Phân tích một PGN

```bash
python scripts/analyze_game.py path/to/game.pgn --output experiments/results/xai_report.json
python scripts/analyze_game.py path/to/game.pgn --engine-depth 18   # phân tích kỹ hơn
python scripts/analyze_game.py path/to/game.pgn --no-stockfish --depth 2
```

Báo cáo JSON giữ lại FEN, SAN/UCI, ba ứng viên tốt nhất kèm biến chính, đòn
trừng phạt, cơ hội thắng, các thành phần điểm và câu giải thích tiếng Việt, nên
UI Pygame hoặc notebook có thể dùng lại mà không phải chạy search lần nữa.
Trường `method` trong từng dòng ghi rõ engine và độ sâu đã dùng.

## Giới hạn cần nêu rõ trong báo cáo

Khi có Stockfish, chất lượng nước đi (nhãn best/blunder, centipawn loss, PV) là
đáng tin ở mức độ sâu đã chọn; nhưng **phần phân rã 8 thành phần và câu giải
thích vẫn dựa trên evaluator nội bộ**, nên là gợi ý sư phạm chứ không phải "lý
do" của Stockfish (mạng NNUE không phân rã được theo cách này). Khi chạy
fallback không có Stockfish, mọi kết luận phụ thuộc evaluator tự viết ở depth
thấp và có thể đổi khi tăng depth — UI hiển thị engine đang dùng và trường
`method` ghi lại điều này trong từng báo cáo.

## Hướng phát triển tiếp theo

1. Cho phép bấm vào một ứng viên trong panel để xem biến thể đáp trả tốt nhất
   ngay trên bàn cờ (hiện mới hiển thị dạng chữ).
2. Lưu lịch sử tổng kết nhiều ván để vẽ tiến bộ theo thời gian (accuracy, ACPL
   qua từng ván; motif để hở giảm dần).
3. Mở rộng bộ motif: quá tải (overloading), đánh lạc hướng (deflection),
   chiếu đôi, đòn phối hợp nhiều nước.
4. Deploy web UI lên hosting công khai để dùng không cần cài Python.
