#!/bin/bash
#
# GitHub Monitor - 部署腳本
# 用於快速部署和管理 Docker 容器
#

set -euo pipefail

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 項目資訊
PROJECT_NAME="github-monitor"
IMAGE_NAME="github-monitor"
CONTAINER_NAME="github-monitor"

# 函數：輸出彩色訊息
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 檢查必要文件
check_prerequisites() {
    log_info "檢查必要文件..."

    if [ ! -f ".env" ]; then
        log_error ".env 文件不存在！"
        log_info "請複製 .env.example 並填入正確的配置："
        echo "  cp .env.example .env"
        echo "  vim .env"
        exit 1
    fi

    if [ ! -f "config.yaml" ]; then
        log_error "config.yaml 不存在！"
        exit 1
    fi

    if [ ! -f "Dockerfile" ]; then
        log_error "Dockerfile 不存在！"
        exit 1
    fi

    # 檢查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安裝！"
        exit 1
    fi

    # 檢查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安裝！"
        exit 1
    fi

    log_info "前置檢查通過 ✓"
}

# 建構映像
build_image() {
    log_info "開始建構 Docker 映像..."

    docker build \
        -t "${IMAGE_NAME}:latest" \
        -t "${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S)" \
        .

    log_info "映像建構完成 ✓"
}

# 啟動服務
start_service() {
    local ENV=${1:-production}

    log_info "啟動服務 (環境: ${ENV})..."

    # 創建日誌目錄
    mkdir -p logs

    case "${ENV}" in
        dev|development)
            docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
            ;;
        prod|production)
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
            ;;
        *)
            docker-compose up -d
            ;;
    esac

    log_info "服務已啟動 ✓"
    log_info "使用以下命令查看日誌："
    echo "  docker-compose logs -f ${CONTAINER_NAME}"
}

# 停止服務
stop_service() {
    log_info "停止服務..."
    docker-compose down
    log_info "服務已停止 ✓"
}

# 重啟服務
restart_service() {
    log_info "重啟服務..."
    stop_service
    start_service "$@"
}

# 查看日誌
view_logs() {
    docker-compose logs -f --tail=100 "${CONTAINER_NAME}"
}

# 查看狀態
show_status() {
    log_info "服務狀態："
    docker-compose ps

    echo ""
    log_info "容器資源使用："
    docker stats --no-stream "${CONTAINER_NAME}" 2>/dev/null || log_warn "容器未運行"

    echo ""
    log_info "健康檢查："
    docker exec "${CONTAINER_NAME}" python healthcheck.py 2>/dev/null || log_warn "健康檢查失敗"
}

# 進入容器
shell_exec() {
    log_info "進入容器 shell..."
    docker exec -it "${CONTAINER_NAME}" /bin/bash || \
    docker exec -it "${CONTAINER_NAME}" /bin/sh
}

# 清理資源
cleanup() {
    log_warn "清理所有資源（包括卷和網絡）..."
    read -p "確定要繼續嗎？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --remove-orphans
        docker rmi "${IMAGE_NAME}:latest" 2>/dev/null || true
        log_info "清理完成 ✓"
    else
        log_info "已取消"
    fi
}

# 備份配置
backup_config() {
    local BACKUP_DIR="backups/$(date +%Y%m%d)"
    log_info "備份配置到 ${BACKUP_DIR}..."

    mkdir -p "${BACKUP_DIR}"
    cp .env "${BACKUP_DIR}/.env.backup"
    cp config.yaml "${BACKUP_DIR}/config.yaml.backup"

    log_info "備份完成 ✓"
}

# 更新服務
update_service() {
    log_info "更新服務..."

    # 備份配置
    backup_config

    # 拉取最新代碼
    if [ -d ".git" ]; then
        git pull
    fi

    # 重新建構
    build_image

    # 重啟服務
    restart_service "$@"

    log_info "更新完成 ✓"
}

# 顯示幫助
show_help() {
    cat << EOF
GitHub Monitor - 部署管理腳本

用法: $0 [命令] [選項]

命令:
  check       檢查前置條件
  build       建構 Docker 映像
  start       啟動服務 [dev|prod]
  stop        停止服務
  restart     重啟服務 [dev|prod]
  logs        查看日誌
  status      查看服務狀態
  shell       進入容器 shell
  update      更新服務
  backup      備份配置
  cleanup     清理所有資源
  help        顯示此幫助訊息

範例:
  $0 check                    # 檢查環境
  $0 build                    # 建構映像
  $0 start prod               # 啟動生產環境
  $0 logs                     # 查看日誌
  $0 status                   # 查看狀態

EOF
}

# 主程式
main() {
    local COMMAND=${1:-help}

    case "${COMMAND}" in
        check)
            check_prerequisites
            ;;
        build)
            check_prerequisites
            build_image
            ;;
        start)
            check_prerequisites
            start_service "${2:-production}"
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service "${2:-production}"
            ;;
        logs)
            view_logs
            ;;
        status)
            show_status
            ;;
        shell)
            shell_exec
            ;;
        update)
            update_service "${2:-production}"
            ;;
        backup)
            backup_config
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: ${COMMAND}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
