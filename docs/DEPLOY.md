# Đưa Chess XAI Tutor lên web (miễn phí)

Web app cần chạy Python + Stockfish trên máy chủ, nên không dùng được các dịch
vụ host trang tĩnh (GitHub Pages, Netlify). Repo đã có sẵn `Dockerfile` (tự tải
Stockfish bản Linux khi build), `wsgi.py` và `requirements-web.txt`; deploy
được lên bất kỳ nơi nào chạy Docker. Dưới đây là cách miễn phí đơn giản nhất.

## Cách 1 — Hugging Face Spaces (khuyên dùng, không cần thẻ)

Gói miễn phí: 2 vCPU, 16GB RAM, không hết hạn. Space "ngủ" sau 48 giờ không
ai truy cập và tự dậy khi có người vào (mất ~30 giây lần đầu).

1. Tạo tài khoản tại <https://huggingface.co/join> — chọn **username** cẩn thận
   vì nó nằm trong link web: `https://huggingface.co/spaces/<username>/<tên-space>`.
2. Vào <https://huggingface.co/new-space>:
   - **Space name**: ví dụ `chess-xai-tutor`
   - **License**: MIT (hoặc để trống)
   - **SDK**: chọn **Docker** → **Blank**
   - **Space hardware**: CPU basic (Free)
   - **Public** → bấm **Create Space**.
3. Tạo access token để push: avatar → **Settings** → **Access Tokens** →
   **Create new token**, quyền **Write**. Copy token (chỉ hiện một lần).
4. Trên máy bạn, trong thư mục dự án:

   ```bash
   git remote add hf https://huggingface.co/spaces/<username>/chess-xai-tutor
   git push hf main --force
   ```

   Khi hỏi mật khẩu, dán **token** (không phải mật khẩu tài khoản).
   Lần đầu HF build image ~3–5 phút (tải Stockfish + cài thư viện); theo dõi ở
   tab **Logs** của Space. Xong sẽ thấy trạng thái **Running** và web ở
   `https://<username>-chess-xai-tutor.hf.space`.

Cấu hình Space nằm ở khối YAML đầu `README.md` (`sdk: docker`, `app_port: 7860`)
— đừng xoá khối đó. Nếu CPU chậm, vào **Settings → Variables** thêm
`XAI_ENGINE_DEPTH=12` để phân tích nhanh hơn.

Cập nhật web sau này: commit rồi `git push hf main`.

## Cách 2 — Render (có tên miền riêng miễn phí, nhưng máy yếu hơn)

Gói free: 512MB RAM, ngủ sau 15 phút không dùng (dậy ~1 phút). Được gắn tên
miền riêng miễn phí.

1. Đăng ký <https://render.com> bằng GitHub.
2. **New → Web Service** → chọn repo `chess-xai-tutor` → Runtime **Docker**
   → Instance type **Free** → **Create**.
3. Render tự đọc `Dockerfile` và biến `PORT`. Nên thêm biến môi trường
   `XAI_ENGINE_DEPTH=10` và `XAI_MULTIPV=3` vì CPU gói free yếu.

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

- Link miễn phí kèm theo: `*.hf.space` (Hugging Face) hoặc `*.onrender.com`.
- Sinh viên: **GitHub Student Developer Pack** (<https://education.github.com/pack>)
  tặng 1 năm tên miền `.me` (Namecheap) — miễn phí và hợp lệ.
- Mua: `.xyz` vài chục nghìn đồng/năm đầu, `.com` ~250k/năm (Namecheap, Porkbun).
  Gói free của Hugging Face không cho gắn tên miền riêng; Render thì có.

## Chạy bằng Docker ở bất kỳ đâu

```bash
docker build -t chess-xai-tutor .
docker run -p 7860:7860 chess-xai-tutor
# mở http://127.0.0.1:7860
```

Biến môi trường hỗ trợ: `PORT`, `XAI_ENGINE_DEPTH`, `XAI_MULTIPV`,
`XAI_USE_STOCKFISH=0` (tắt Stockfish), `STOCKFISH_PATH`.

## Lưu ý nếu định thương mại hoá

- Các gói miễn phí ở trên dành cho demo/dự án cá nhân; khi có người dùng trả
  phí cần máy chủ riêng (VPS ~100–150k đồng/tháng như Hetzner, DigitalOcean)
  cùng đăng nhập, thanh toán và giới hạn số ván/ngày.
- Stockfish và python-chess đều theo giấy phép **GPLv3**: chạy dưới dạng dịch vụ
  web (SaaS) là được; nhưng nếu phát hành phần mềm cài về máy có kèm chúng thì
  phải công khai mã nguồn theo GPL. Giữ mô hình "dịch vụ web" là an toàn nhất.
