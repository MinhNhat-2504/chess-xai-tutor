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
`engine_time_s`, `multipv`, `use_stockfish`).

**Tốc độ:** mặc định depth 12 với nắp 1 giây mỗi lần tìm kiếm — đo thực tế trên
ván 140 nửa nước: ~50 giây (0,36 s/nước), và kết luận sai/không-sai trùng với
depth 16 ở mức 94%, ngang depth 14 nhưng nhanh gấp 3. Oracle cache theo FEN nên
khi phân tích cả ván, điểm của nước đã đi lấy từ phân tích thế kế tiếp (cách
Lichess làm) — mỗi vị trí chỉ chạy engine đúng một lần. Web có lựa chọn
**Nhanh (depth 12) / Kỹ (depth 16, chậm ~3 lần)** cho ván quan trọng.

## Ứng dụng đồ hoạ cho người học

Mở ứng dụng bằng lệnh sau:

```bash
python scripts/xai_viewer.py                 # tự dò Stockfish, depth 12
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

Mở trình duyệt tại địa chỉ script in ra (mặc định `http://127.0.0.1:8000`;
nếu cổng bị Windows chặn, script tự chọn cổng khác), dán PGN (Chess.com: vào
ván đấu → Share → tab PGN → copy) hoặc chọn file `.pgn`, bấm **Phân tích ván
cờ**. Kết quả hiện dần từng nước trong lúc phân tích chạy nền.

Giao diện được thiết kế cho người học, không dùng thuật ngữ kỹ thuật:

- Mỗi nước: nhãn chất lượng, **thanh cơ hội thắng** (so với nếu đi nước tốt
  nhất), câu giải thích tiếng Việt, "điều gì đang xảy ra trên bàn cờ" (đòn
  đôi, ghim, ăn quân, chiếu...), điểm cộng/điểm trừ về thế trận, các nước đáng
  cân nhắc kèm cơ hội thắng.
- Với nước sai: mũi tên xanh chỉ nước nên đi, và hai nút **"Xem đối thủ trừng
  phạt thế nào ▶"** / **"Xem nước nên đi ▶"** phát lại biến **từng bước ngay
  trên bàn cờ**, mỗi bước có mũi tên và chú thích ("đòn đôi: mã c2 tấn công
  cùng lúc xe a1 và vua e1", "ăn xe (5 điểm)", "chiếu hết"). Có chế độ tự chạy,
  và gợi ý người học tự đoán nước kế tiếp trước khi bấm — đây là cách luyện mắt
  nhìn đòn chiến thuật, không chỉ biết mình đã blunder.
- Tổng kết ván: độ chính xác từng bên, lỗi theo giai đoạn, danh sách nước nên
  xem lại (bấm là nhảy tới), và chủ đề chiến thuật nên luyện.

Điều hướng bằng phím `←`/`→`, nút "Nước sai kế tiếp" nhảy tới chỗ cần học.

Trang web tự chứa (không cần internet), chỉ chạy trên máy bạn (`127.0.0.1`).
Tuỳ chọn: `--port`, `--engine-depth`, `--no-stockfish`.

## Ván của tôi, hồ sơ điểm yếu và bài tập cá nhân

Ba tab tiếp theo trên web biến "phân tích" thành "học":

- **Ván của tôi** — nhập tên Chess.com hoặc Lichess (API công khai, không cần
  đăng nhập), chọn 10/20/50 ván → hệ thống tự kéo và phân tích các ván bạn
  chơi, lưu vào `data/tutor.db` (SQLite; đổi bằng biến `XAI_DB_PATH`). Nhập lại
  không phân tích trùng. Bấm vào ván để mở lại trong viewer (bàn cờ tự xoay
  theo màu bạn cầm).
- **Hồ sơ điểm yếu** (`src/xai/profile.py`) — chỉ tính **nước của chính bạn**:
  độ chính xác trung bình và xu hướng, thắng/hoà/thua, tỉ lệ lỗi theo khai/
  trung/tàn cuộc, đòn hay để hở (đòn đôi, ghim...), khai cuộc chơi tệ nhất và
  thường sai từ nước mấy, các nước tệ nhất (bấm để mở lại). Kèm 3–5 câu nhận
  xét tiếng Việt.
- **Luyện tập** (`src/xai/store.py`) — mỗi sai lầm/blunder có đòn trừng phạt
  mang yếu tố chiến thuật (ăn quân, chiếu, đòn đôi/ghim/xiên/mở, đe doạ) sinh
  một bài "tìm đòn trừng phạt": bấm quân rồi bấm ô đích; đáp án khác nhưng
  ngang sức (Stockfish chấm chênh ≤ 30cp) vẫn được tính đúng. Lịch **ôn ngắt
  quãng** kiểu Leitner: đúng thì giãn 1 → 3 → 7 → 14 → 30 → 60 ngày, sai thì
  về 1 ngày. Bài từ lỗi của bạn dạy bạn thấy đòn mình để hở; bài từ lỗi của
  đối thủ dạy bạn không bỏ lỡ cơ hội.

Trên Hugging Face Spaces gói free, ổ đĩa không bền — dữ liệu mất khi Space
khởi động lại; chạy local hoặc VPS thì giữ được.

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
python scripts/analyze_game.py path/to/game.pgn --engine-depth 16   # phân tích kỹ hơn (chậm ~3 lần)
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
