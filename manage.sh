#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="/home/alex/WEB_NST"
cd "$PROJECT_DIR"

get_port() {
    PORT=$(grep -E "^[[:space:]]*PORT\s*=\s*[0-9]+" config.py 2>/dev/null | grep -oE '[0-9]+' | head -1)
    if [ -z "$PORT" ]; then
        PORT=5000
    fi
    echo "$PORT"
}

get_ip() {
    IP=$(hostname -I | awk '{print $1}')
    if [ -z "$IP" ]; then
        IP="localhost"
    fi
    echo "$IP"
}

status() {
    if lsof -i :5000 > /dev/null 2>&1 2>/dev/null; then
        PID=$(lsof -t -i :5000 2>/dev/null | head -1)
        PORT=$(get_port)
        IP=$(get_ip)
        WORKERS=$(lsof -t -i :5000 2>/dev/null | wc -l)
        echo -e "${GREEN}✅ Сервер запущен${NC}"
        echo -e "${GREEN}   Главный PID: $PID${NC}"
        echo -e "${GREEN}   Воркеров: $WORKERS${NC}"
        echo -e "${GREEN}🌐 Локальный адрес: http://localhost:${PORT}${NC}"
        echo -e "${GREEN}🌐 Сетевой адрес: http://${IP}:${PORT}${NC}"
        return 0
    else
        echo -e "${RED}❌ Сервер не запущен${NC}"
        return 1
    fi
}

stop() {
    echo -e "${YELLOW}🛑 Остановка сервера...${NC}"
    
    echo "========== $(date) - ОСТАНОВКА СЕРВЕРА ==========" >> logs/gunicorn.log
    
    # Жесткая очистка порта 5000
    fuser -k 5000/tcp 2>/dev/null
    lsof -t -i :5000 2>/dev/null | xargs kill -9 2>/dev/null
    
    # Убиваем все связанные процессы
    pkill -9 -f "gunicorn" 2>/dev/null
    pkill -9 -f "api_server" 2>/dev/null
    pkill -9 -f "wsgi" 2>/dev/null
    pkill -9 -f "python.*gunicorn" 2>/dev/null
    
    rm -f gunicorn.pid
    
    sleep 3
    
    # Проверяем, что порт действительно освободился
    if lsof -i :5000 > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ Порт 5000 всё ещё занят. Принудительная очистка...${NC}"
        fuser -k 5000/tcp 2>/dev/null
        lsof -t -i :5000 2>/dev/null | xargs kill -9 2>/dev/null
        sleep 2
    fi
    
    echo -e "${GREEN}✅ Сервер остановлен${NC}"
}

start() {
    # Сначала убедимся, что порт свободен
    if lsof -i :5000 > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ Порт 5000 занят. Останавливаем старые процессы...${NC}"
        stop
    fi
    
    echo -e "${GREEN}🚀 Запуск Gunicorn сервера...${NC}"
    
    mkdir -p logs orders backup temp database
    
    cd "$PROJECT_DIR"
    
    # Проверка venv
    if [ ! -f "venv/bin/activate" ]; then
        echo -e "${RED}❌ Виртуальное окружение не найдено${NC}"
        return 1
    fi
    
    source venv/bin/activate
    
    PORT=$(get_port)
    
    echo "========== $(date) - ЗАПУСК СЕРВЕРА ==========" >> logs/gunicorn.log
    
    NUM_CORES=$(nproc)
    WORKERS=$((2 * NUM_CORES + 1))
    if [ $WORKERS -gt 25 ]; then
        WORKERS=25
    fi
    
    # Запуск с перенаправлением вывода
    "$PROJECT_DIR/venv/bin/python" -u -m gunicorn --workers $WORKERS \
                   --bind 0.0.0.0:$PORT \
                   --timeout 120 \
                   --access-logfile logs/access.log \
                   --error-logfile logs/error.log \
                   --log-level info \
                   wsgi:app >> logs/gunicorn.log 2>&1 &
    
    GUNICORN_PID=$!
    echo $GUNICORN_PID > gunicorn.pid
    
    sleep 3
    
    if status > /dev/null 2>&1; then
        IP=$(get_ip)
        echo -e "${GREEN}✅ Сервер успешно запущен${NC}"
        echo -e "${GREEN}🌐 Локальный адрес: http://localhost:${PORT}${NC}"
        echo -e "${GREEN}🌐 Сетевой адрес: http://${IP}:${PORT}${NC}"
        echo -e "${YELLOW}📝 Логи: ./manage.sh logs${NC}"
        return 0
    else
        echo -e "${RED}❌ Ошибка запуска. Проверьте logs/gunicorn.log${NC}"
        echo -e "${YELLOW}Последние 10 строк лога:${NC}"
        tail -10 logs/gunicorn.log 2>/dev/null
        return 1
    fi
}

restart() {
    echo -e "${YELLOW}🔄 Перезапуск сервера...${NC}"
    stop
    sleep 3
    start
}

logs() {
    if [ -f "logs/gunicorn.log" ]; then
        echo -e "${BLUE}📋 Логи Gunicorn (Ctrl+C для выхода)${NC}"
        echo -e "${YELLOW}================================${NC}"
        tail -f logs/gunicorn.log
    else
        echo -e "${RED}❌ Файл логов не найден: logs/gunicorn.log${NC}"
    fi
}

access() {
    if [ -f "logs/access.log" ]; then
        echo -e "${BLUE}📋 Access логи (Ctrl+C для выхода)${NC}"
        tail -f logs/access.log
    else
        echo -e "${RED}❌ Файл access логов не найден${NC}"
    fi
}

error() {
    if [ -f "logs/error.log" ]; then
        echo -e "${BLUE}📋 Error логи (Ctrl+C для выхода)${NC}"
        tail -f logs/error.log
    else
        echo -e "${RED}❌ Файл error логов не найден${NC}"
    fi
}

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    logs) logs ;;
    access) access ;;
    error) error ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|access|error}"
        echo ""
        echo "Команды:"
        echo "  start   - запустить сервер"
        echo "  stop    - остановить сервер"
        echo "  restart - перезапустить сервер"
        echo "  status  - проверить статус"
        echo "  logs    - просмотреть основной лог"
        echo "  access  - просмотреть access лог"
        echo "  error   - просмотреть error лог"
        exit 1
        ;;
esac
