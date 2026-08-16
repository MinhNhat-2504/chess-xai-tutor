# Chess XAI Tutor — image chạy web app kèm Stockfish (Linux).
# Dùng cho Hugging Face Spaces (Docker), Render, hoặc bất kỳ máy chủ Docker nào.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STOCKFISH_PATH=/app/engines/stockfish/stockfish \
    PORT=7860

WORKDIR /app

# Stockfish bản Linux chính thức (thư mục engines/ nằm trong .gitignore nên
# không có sẵn trong repo — tải lúc build).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && mkdir -p /app/engines/stockfish \
    && curl -fsSL -o /tmp/sf.tar \
       https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-avx2.tar \
    && tar -xf /tmp/sf.tar -C /tmp \
    && mv /tmp/stockfish/stockfish-ubuntu-x86-64-avx2 /app/engines/stockfish/stockfish \
    && chmod +x /app/engines/stockfish/stockfish \
    && rm -rf /tmp/sf.tar /tmp/stockfish \
    && apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Chỉ cài thư viện cần cho web (bỏ pygame/matplotlib cho image nhẹ).
COPY requirements-web.txt .
RUN pip install -r requirements-web.txt

COPY config ./config
COPY src ./src
COPY wsgi.py .

# Hugging Face Spaces chạy container với user không phải root.
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 7860
CMD ["sh", "-c", "waitress-serve --host 0.0.0.0 --port ${PORT} --threads 8 wsgi:app"]
