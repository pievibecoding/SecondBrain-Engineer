#!/usr/bin/env bash
set -euo pipefail

echo "=== SecondBrain — First-time setup ==="

# 1. Tạo .env từ template nếu chưa có
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Tạo .env từ .env.example — hãy điền các giá trị thực vào .env"
else
    echo "ℹ️  .env đã tồn tại — bỏ qua"
fi

# 2. Tạo lightrag .env từ template nếu chưa có
if [ ! -f lightrag/.env ]; then
    cp lightrag/.env.example lightrag/.env 2>/dev/null || \
    echo "⚠️  Không tìm thấy lightrag/.env.example — cần tạo thủ công"
else
    echo "ℹ️  lightrag/.env đã tồn tại — bỏ qua"
fi

# 3. Tạo thư mục storage cho LightRAG
mkdir -p lightrag/storage
echo "✅ Tạo lightrag/storage/"

echo ""
echo "=== Bước tiếp theo ==="
echo "1. Điền giá trị thực vào .env và lightrag/.env"
echo "2. Mount NAS: sudo mount -t cifs //NAS_HOST/documents /mnt/synology -o username=secondbrain,..."
echo "3. Chạy stack: docker compose up -d"
echo "4. Kiểm tra: python scripts/seed-test-data.py"
