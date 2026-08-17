# Đưa Chess XAI Tutor lên web (miễn phí)

Web app cần chạy Python + Stockfish trên máy chủ, nên không dùng được các dịch
vụ host trang tĩnh (GitHub Pages, Netlify). Repo đã có sẵn `Dockerfile` (tự tải
Stockfish bản Linux khi build), `wsgi.py` và `requirements-web.txt`; deploy
được lên bất kỳ nơi nào chạy Docker. Dưới đây là cách miễn phí đơn giản nhất.

## Cách 1 — Render (miễn phí, không cần thẻ, khuyên dùng)

> Lưu ý: từ 2026 Hugging Face Spaces yêu cầu gói trả phí cho Docker/Gradio
> (chỉ Static Space còn miễn phí), nên không dùng được cho app này nữa.

Gói free của Render: 512MB RAM, CPU yếu (0,1 nhân), ngủ sau 15 phút không ai
dùng và tự dậy khi có người vào (~1 phút). Được gắn tên miền riêng miễn phí.
Repo đã có `render.yaml` cấu hình sẵn (depth 10, nắp 0,6 giây để hợp CPU yếu).

1. Vào <https://render.com> → **Get Started** → đăng ký bằng **GitHub** (bấm
   Authorize để Render thấy repo của bạn). Không cần thẻ.
2. Trong Dashboard bấm **New +** → **Blueprint**.
3. Chọn repo `chess-xai-tutor` (nếu chưa thấy, bấm *Configure account* để cấp
   quyền cho repo đó) → Render đọc `render.yaml` → **Apply**.
4. Chờ build ~5–8 phút (tải Stockfish + cài thư viện). Xem tiến trình ở tab
   **Logs**; xong sẽ thấy **Live** và link dạng
   `https://chess-xai-tutor-xxxx.onrender.com`.

Cập nhật sau này: cứ push lên GitHub, Render tự build lại (Auto-Deploy).

Muốn tên miền riêng: **Settings → Custom Domains** trên Render, rồi trỏ CNAME
ở nơi mua tên miền.

## Cách 2 — Máy chủ Docker bất kỳ (VPS)

Khi cần mạnh hơn/giữ dữ liệu lâu dài: VPS ~100–150k đồng/tháng (Hetzner,
DigitalOcean, Vultr) chạy Docker:

```bash
git clone https://github.com/MinhNhat-2504/chess-xai-tutor.git && cd chess-xai-tutor
docker build -t chess-xai-tutor .
docker run -d --restart unless-stopped -p 80:7860 -v $PWD/data:/app/data chess-xai-tutor
```

(`-v` giữ `data/tutor.db` ngoài container để không mất khi cập nhật.)

## Cách 3 — Chạy trên máy bạn, chia sẻ link tạm (demo cho bạn bè/thầy cô)

Không cần host: cài `cloudflared`
(<https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/downloads/>)
rồi chạy hai cửa sổ:

```bash
python scripts/web_app.py --port 8777
cloudflared tunnel --url http://127.0.0.1:8777
```

`cloudflared` in ra một link `https://....trycloudflare.com` dùng được ngay,
tắt cửa sổ là link hết hiệu lực.

## Tên miền

- Link miễn phí kèm theo: `*.onrender.com`.
- Sinh viên: **GitHub Student Developer Pack** (<https://education.github.com/pack>)
  tặng 1 năm tên miền `.me` (Namecheap) — miễn phí và hợp lệ.
- Mua: `.xyz` vài chục nghìn đồng/năm đầu, `.com` ~250k/năm (Namecheap, Porkbun).
  Render gói free cho gắn tên miền riêng.

## Chạy bằng Docker ở bất kỳ đâu

```bash
docker build -t chess-xai-tutor .
docker run -p 7860:7860 chess-xai-tutor
# mở http://127.0.0.1:7860
```

Biến môi trường hỗ trợ: `PORT`, `XAI_ENGINE_DEPTH`, `XAI_MULTIPV`,
`XAI_USE_STOCKFISH=0` (tắt Stockfish), `STOCKFISH_PATH`.

## Dữ liệu người dùng (ván đã phân tích, bài tập)

Lưu trong SQLite `data/tutor.db` (đổi bằng biến `XAI_DB_PATH`). Render gói
free **không giữ ổ đĩa** khi khởi động lại — dữ liệu sẽ
mất; đủ cho demo, còn muốn giữ hồ sơ người dùng lâu dài thì cần VPS hoặc gói có
persistent storage.

## Lưu ý nếu định thương mại hoá

- Các gói miễn phí ở trên dành cho demo/dự án cá nhân; khi có người dùng trả
  phí cần máy chủ riêng (VPS ~100–150k đồng/tháng như Hetzner, DigitalOcean)
  cùng đăng nhập, thanh toán và giới hạn số ván/ngày.
- Stockfish và python-chess đều theo giấy phép **GPLv3**: chạy dưới dạng dịch vụ
  web (SaaS) là được; nhưng nếu phát hành phần mềm cài về máy có kèm chúng thì
  phải công khai mã nguồn theo GPL. Giữ mô hình "dịch vụ web" là an toàn nhất.
