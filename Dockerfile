FROM python:3.9-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有代碼
COPY . .

# 建立必要資料夾並設定權限
RUN mkdir -p /app/data /app/temp_downloads /app/logs && \\
    chmod 755 /app/data /app/temp_downloads /app/logs

# 設定環境變數
ENV DATA_FOLDER=/app/data
ENV CLOUD_PROVIDER=local
ENV PYTHONPATH=/app:/app/api:/app/controllers:/app/models:/app/utils
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
CMD curl -f http://localhost:8000/health || exit 1

# 啟動命令
CMD ["python", "api/main.py"]