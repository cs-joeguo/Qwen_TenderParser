#!/bin/bash

# 启动招标信息处理服务的脚本（后台运行版）

# 检查Python是否可用（同时支持python和python3命令）
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    # 检查python是否指向Python 3
    if python --version 2>&1 | grep -q "Python 3"; then
        PYTHON_CMD="python"
    else
        echo "错误: 找到的python不是Python 3，请安装Python 3后再试"
        exit 1
    fi
else
    echo "错误: 未找到Python 3，请安装Python 3后再试"
    exit 1
fi

# 定义项目根目录（根据实际情况调整，此处假设脚本位于项目根目录）
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# 定义日志文件和PID文件路径
LOG_FILE="$PROJECT_DIR/service.log"  # 系统级日志（启动/崩溃信息）
PID_FILE="$PROJECT_DIR/service.pid"
APP_LOG_DIR="$PROJECT_DIR/logs"      # 应用业务日志目录
APP_LOG_FILE="$APP_LOG_DIR/tender_service.log"  # 应用业务日志文件

# 进入项目目录
cd "$PROJECT_DIR" || {
    echo "错误: 无法进入项目目录 $PROJECT_DIR"
    exit 1
}

# 检查服务是否已在运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null; then
            return 0  # 服务正在运行
        else
            rm -f "$PID_FILE"  # PID文件存在但进程不存在，清理文件
        fi
    fi
    return 1  # 服务未运行
}

# 启动服务
start_service() {
    if is_running; then
        echo "服务已在运行中 (PID: $(cat "$PID_FILE"))"
        return 0
    fi

    # 关键修改1：确保应用日志目录存在（自动创建logs文件夹）
    mkdir -p "$APP_LOG_DIR"
    if [ ! -d "$APP_LOG_DIR" ]; then
        echo "错误: 无法创建日志目录 $APP_LOG_DIR，请检查权限"
        exit 1
    fi

    # 可选：创建并激活虚拟环境
    # if [ ! -d "venv" ]; then
    #     $PYTHON_CMD -m venv venv
    #     echo "已创建虚拟环境"
    # fi
    # source venv/bin/activate

    echo "启动招标信息处理服务..."
    # 关键修改2：仅重定向系统级输出（避免覆盖应用日志）
    # 应用业务日志由Python的logging模块写入 $APP_LOG_FILE
    $PYTHON_CMD main.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    echo "服务已启动 (PID: $(cat "$PID_FILE"))"
    echo "系统日志文件: $LOG_FILE"       # 记录启动信息、未捕获异常等
    echo "应用业务日志文件: $APP_LOG_FILE"  # 记录logger.info等业务日志
}

# 停止服务
stop_service() {
    if ! is_running; then
        echo "服务未在运行"
        return 0
    fi

    local pid=$(cat "$PID_FILE")
    echo "正在停止服务 (PID: $pid)..."
    kill "$pid"
    
    # 等待进程结束
    local count=0
    while ps -p "$pid" > /dev/null; do
        sleep 1
        count=$((count + 1))
        if [ $count -ge 10 ]; then
            echo "强制终止服务..."
            kill -9 "$pid"
            break
        fi
    done
    
    rm -f "$PID_FILE"
    echo "服务已停止"
}

# 查看服务状态
check_status() {
    if is_running; then
        echo "服务正在运行 (PID: $(cat "$PID_FILE"))"
        echo "系统日志文件: $LOG_FILE"
        echo "应用业务日志文件: $APP_LOG_FILE"
    else
        echo "服务未在运行"
    fi
}

# 查看日志（默认查看应用业务日志，可按需切换）
view_logs() {
    # 关键修改3：默认查看应用业务日志，更符合日常调试需求
    if [ "$2" = "system" ]; then
        # 查看系统日志（如启动失败原因）：sh start.sh logs system
        target_log="$LOG_FILE"
    else
        # 查看应用业务日志（如logger.info输出）：sh start.sh logs
        target_log="$APP_LOG_FILE"
    fi

    if [ -f "$target_log" ]; then
        echo "显示最新日志 (按Ctrl+C退出)，日志文件: $target_log..."
        tail -f "$target_log"
    else
        echo "日志文件不存在: $target_log"
    fi
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [命令]"
    echo "命令:"
    echo "  start   - 启动服务"
    echo "  stop    - 停止服务"
    echo "  restart - 重启服务"
    echo "  status  - 查看服务状态"
    echo "  logs    - 查看应用业务日志（默认）"
    echo "  logs system - 查看系统日志（启动/崩溃信息）"
    echo "  help    - 显示帮助信息"
}

# 根据参数执行相应操作
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        start_service
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs "$@"
        ;;
    help)
        show_help
        ;;
    *)
        # 如果没有参数，默认启动服务
        start_service
        ;;
esac