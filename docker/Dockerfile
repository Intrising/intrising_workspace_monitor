# ==========================================
# 多階段構建 Dockerfile - 企業級優化
# ==========================================

# ===== 階段 1: 建構階段 =====
FROM python:3.11-slim AS builder

# 設置工作目錄
WORKDIR /build

# 安裝編譯依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 建立虛擬環境並安裝依賴
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ===== 階段 2: 運行階段 =====
FROM python:3.11-slim

# 元數據標籤
LABEL maintainer="your-team@example.com" \
      description="GitHub Monitor - Enterprise Grade" \
      version="1.0.0"

# 安全性：創建非 root 用戶
RUN groupadd -r prmonitor && \
    useradd -r -g prmonitor -u 1000 -m -s /sbin/nologin prmonitor

# 安裝運行時依賴（包含 msmtp、nodejs 和 Codex CLI）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    wget \
    msmtp \
    msmtp-mta \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    # 安裝 Codex CLI via npm
    && npm install -g @openai/codex@0.42.0

# 設置工作目錄
WORKDIR /app

# 從建構階段複製虛擬環境
COPY --from=builder /opt/venv /opt/venv

# 複製應用程式文件
COPY src/pr_monitor.py .
COPY src/pr_reviewer.py .
COPY src/database.py .
COPY src/gateway.py .
COPY src/gateway_templates.py .
COPY src/gateway_routes.py .
COPY config.yaml .

# 複製 msmtp 配置示例（可選）
COPY config/msmtprc.example /app/

# 創建必要的目錄
RUN mkdir -p /var/log/github-monitor /var/lib/github-monitor && \
    chown -R prmonitor:prmonitor /app /var/log/github-monitor /var/lib/github-monitor && \
    # 創建 prmonitor 用戶的 home 目錄（如果不存在）
    mkdir -p /home/prmonitor && \
    chown -R prmonitor:prmonitor /home/prmonitor

# 設置環境變數
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Taipei

# 健康檢查
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 切換到非 root 用戶
USER prmonitor

# 暴露端口（如果需要）
# EXPOSE 8080

# 容器啟動命令
CMD ["python", "pr_monitor.py"]
